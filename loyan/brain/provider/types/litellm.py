"""LiteLLM 统一模型提供商 — 经 litellm 单接口调用 100+ 平台（单文件完整封装）

chat() 返回:
    {"content": str, "model": str, "usage": {"prompt","completion","total"}, "time": float}

chat_stream() 产出:
    {"type": "text", "content": str}
    {"type": "done", "usage": {...}, "time": float}

模型名: 任意 litellm 前缀形态（openai/gpt-4o、anthropic/claude-3-5、
ollama/llama3、gemini/...、deepseek/...）；配置 model_prefix 可统一加前缀。
模型 ID 不硬编码：面板手动填写，list_models 从 litellm 模型库动态获取。

本文件包含完整封装：
    - 消息转换与多模态图片（URL/data:image/本地文件 → image_url 段）
    - 流式 thinking 剥离（DeepSeek-R1 等推理模型）+ 流式工具调用组装
    - usage/token 归一化（各 provider 形态 → 统一结构）
    - 模型能力探测（vision / function calling / 上下文长度）
    - 错误映射（litellm 异常 → loyan.brain.provider.errors）
"""

import base64
import logging
import os
import re
import time
from typing import Any, AsyncIterator, Optional

import litellm
from litellm.exceptions import (
    APIError as LiteLLMAPIError,
    AuthenticationError as LiteLLMAuthError,
    BadRequestError as LiteLLMBadRequest,
    ContextWindowExceededError,
    NotFoundError as LiteLLMNotFound,
    RateLimitError as LiteLLMRateLimit,
    Timeout as LiteLLMTimeout,
)

from loyan.brain.provider.base import BaseProvider, register_provider
from loyan.brain.provider.errors import (
    AuthError,
    ModelNotAvailableError,
    ProviderNotAvailableError,
    QuotaExceededError,
    RateLimitError,
    TimeoutError,
)

_logger = logging.getLogger("Brain.provider.litellm")

# ═══════════════════════════ 消息转换（多模态） ═══════════════════════════


def resolve_image(value: Any) -> dict:
    """图片值 → OpenAI image_url 消息段（URL / data:image / 本地文件）"""
    if isinstance(value, str):
        v = value.strip()
        if v.startswith(("http://", "https://", "data:image")):
            return {"type": "image_url", "image_url": {"url": v}}
        if os.path.isfile(v):
            with open(v, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    if isinstance(value, dict):
        url = value.get("url", "")
        if url:
            return {"type": "image_url", "image_url": {"url": url}}
    return {"type": "text", "text": str(value)}


def normalize_messages(messages: list) -> list:
    """消息列表 → litellm 格式；images/image_urls 字段拆入多模态 content 数组"""
    out = []
    for msg in messages:
        m = dict(msg)
        images = m.pop("images", None) or m.pop("image_urls", None)
        if not images:
            out.append(m)
            continue
        content = m.get("content", "")
        parts = []
        if content:
            parts.append({"type": "text", "text": str(content)})
        for img in images:
            parts.append(resolve_image(img))
        m["content"] = parts
        out.append(m)
    return out


# ═══════════════════════════ 流式组装（thinking / 工具调用） ═══════════════════════════

_THINK_OPEN = "<thinking>"
_THINK_CLOSE = "</thinking>"


class ThinkStrip:
    """流式 thinking 状态机：feed 每段文本，产出 (kind, text) 片段

    kind: "text"（正文）/ "reasoning"（思考内容）
    remove=True 时正文剔除思考；emit_reasoning=True 时思考内容透传。
    """

    def __init__(self, remove: bool = True, emit_reasoning: bool = False):
        self.remove = remove
        self.emit_reasoning = emit_reasoning
        self._buf = ""
        self._in_think = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        """喂入增量文本，返回应下发的 (kind, text) 片段列表"""
        self._buf += text
        out = []
        while True:
            if not self._in_think:
                idx = self._buf.find(_THINK_OPEN)
                if idx == -1:
                    if self._buf:
                        out.append(("text", self._buf))
                        self._buf = ""
                    break
                head = self._buf[:idx]
                if head:
                    out.append(("text", head))
                self._buf = self._buf[idx + len(_THINK_OPEN):]
                self._in_think = True
                continue
            idx = self._buf.find(_THINK_CLOSE)
            if idx == -1:
                if self.emit_reasoning and self._buf:
                    out.append(("reasoning", self._buf))
                    self._buf = ""
                break
            if self.emit_reasoning:
                out.append(("reasoning", self._buf[:idx]))
            self._buf = self._buf[idx + len(_THINK_CLOSE):]
            self._in_think = False
        return out

    def flush(self) -> tuple[str, str] | None:
        """流结束：吐出残留片段（(kind, text) 或 None）"""
        tail, self._buf = self._buf, ""
        if not tail:
            return None
        if self._in_think:
            if self.remove:
                return None
            return ("reasoning", tail)
        return ("text", tail)


def strip_think_block(content: str) -> str:
    """非流式：剔除完整 thinking 块"""
    return re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.S).strip()


class ToolCallBuffer:
    """流式工具调用组装：delta.tool_calls 增量 → 完整调用列表"""

    def __init__(self):
        self._calls: dict[int, dict] = {}

    def feed(self, tool_calls: Any) -> None:
        for tc in tool_calls:
            idx = tc.index
            call = self._calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
            if tc.id:
                call["id"] = tc.id
            fn = tc.function
            if fn.name:
                call["name"] += fn.name
            if fn.arguments:
                call["arguments"] += fn.arguments

    def collect(self) -> list[dict]:
        """取回完整调用（未完成/空的丢弃）"""
        out = []
        for idx in sorted(self._calls):
            call = self._calls[idx]
            if call["name"] and call["arguments"]:
                out.append({
                    "id": call["id"],
                    "type": "function",
                    "function": {"name": call["name"], "arguments": call["arguments"]},
                })
        return out

    def reset(self) -> None:
        self._calls.clear()


# ═══════════════════════════ usage 归一化 ═══════════════════════════


def normalize_usage(usage: Any) -> dict:
    """litellm usage（对象/字典/None）→ 统一结构 {"prompt","completion","total"}"""
    if usage is None:
        return {"prompt": 0, "completion": 0, "total": 0}
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        total = usage.get("total_tokens") or (prompt + completion)
        return {"prompt": int(prompt), "completion": int(completion), "total": int(total)}
    prompt = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0
    completion = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0
    total = getattr(usage, "total_tokens", None) or (prompt + completion)
    return {"prompt": int(prompt), "completion": int(completion), "total": int(total)}


# ═══════════════════════════ 模型能力探测 ═══════════════════════════

# 能力探测唯一来源 = litellm.get_model_info（官方模型库，2985+ 模型全量能力数据）。
# 查询失败返回保守默认：vision/推理不支持、上下文 32K、工具调用支持。


def get_model_info(model: str) -> dict:
    """litellm 模型库信息（失败返回空）"""
    try:
        return litellm.get_model_info(model) or {}
    except Exception:
        return {}


def supports_vision(model: str) -> bool:
    """模型是否支持图片输入（litellm 模型库；未知模型保守返回 False）"""
    return bool(get_model_info(model).get("supports_vision"))


def supports_tools(model: str) -> bool:
    """模型是否支持 function calling（litellm 模型库；未知模型保守返回 True）"""
    info = get_model_info(model)
    val = info.get("supports_function_calling")
    if val is not None:
        return bool(val)
    return True


def is_reasoning_model(model: str) -> bool:
    """推理模型（litellm 模型库 supports_reasoning；未知模型返回 False）"""
    return bool(get_model_info(model).get("supports_reasoning"))


def context_length(model: str) -> int:
    """模型上下文长度（litellm 模型库；未知模型返回保守默认 32K）"""
    info = get_model_info(model)
    val = info.get("max_input_tokens") or info.get("max_tokens")
    if val:
        return int(val)
    return 32768


def max_output_tokens(model: str) -> int:
    """模型单次最大输出 tokens（litellm 模型库；未知/异常返回 8192）"""
    try:
        info = get_model_info(model)
        val = info.get("max_output_tokens") or info.get("max_tokens")
        if val and isinstance(val, (int, float)) and val > 0:
            return int(val)
    except Exception:
        pass
    return 8192


# ═══════════════════════════ 厂商预置清单 ═══════════════════════════

# 面板展示用：选中厂商 → 自动填入 model_prefix + api_base，填 key 即可建实例。
# 模型 ID 不硬编码（持续更新）：面板手动填写，或从 litellm 模型库动态获取。
# api_base 为可修改默认值；留空表示依赖环境变量或手动填写。

VENDORS = [
    {"id": "openai", "name": "OpenAI", "icon": "openai.svg", "category": ["chat", "tts", "embedding"], "prefix": "openai",
     "api_base": "https://api.openai.com/v1"},

    {"id": "anthropic", "name": "Anthropic Claude", "icon": "anthropic.svg", "category": ["chat"], "prefix": "anthropic",
     "api_base": "https://api.anthropic.com"},

    {"id": "ollama", "name": "Ollama（本地）", "icon": "ollama.svg", "category": ["chat"], "prefix": "ollama",
     "api_base": "http://localhost:11434"},

    {"id": "gemini", "name": "Google Gemini", "icon": "gemini.svg", "category": ["chat", "embedding"], "prefix": "gemini",
     "api_base": "https://generativelanguage.googleapis.com"},

    {"id": "deepseek", "name": "DeepSeek", "icon": "deepseek.svg", "category": ["chat"], "prefix": "deepseek",
     "api_base": "https://api.deepseek.com"},

    {"id": "zhipu", "name": "智谱 GLM（z.ai）", "icon": "zhipu.svg", "category": ["chat"], "prefix": "zai",
     "api_base": "https://open.bigmodel.cn/api/paas/v4"},

    {"id": "bailian", "name": "阿里云百炼（通义千问）", "icon": "dashscope.png", "category": ["chat", "embedding"], "prefix": "dashscope",
     "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},

    {"id": "siliconflow", "name": "硅基流动 SiliconFlow", "icon": "siliconflow.svg", "category": ["chat"], "prefix": "openai_like",
     "api_base": "https://api.siliconflow.cn/v1",
     "note": "litellm 官方未收录，需在 custom_pricing 配置价格才能计费"},

    {"id": "doubao", "name": "字节豆包（火山方舟）", "icon": "volcengine.svg", "category": ["chat"], "prefix": "volcengine",
     "api_base": "https://ark.cn-beijing.volces.com/api/v3"},

    {"id": "moonshot", "name": "月之暗面 Kimi", "icon": "moonshot.svg", "category": ["chat"], "prefix": "moonshot",
     "api_base": "https://api.moonshot.cn/v1"},

    {"id": "baichuan", "name": "百川智能", "icon": "baichuan.svg", "category": ["chat"], "prefix": "openai_like",
     "api_base": "https://api.baichuan-ai.com/v1",
     "note": "litellm 未收录百川价格，需在 custom_pricing 配置价格才能计费"},

    {"id": "yi", "name": "零一万物", "icon": "yi.svg", "category": ["chat"], "prefix": "openai_like",
     "api_base": "https://api.lingyiwanwu.com/v1",
     "note": "litellm 未收录零一价格，需在 custom_pricing 配置价格才能计费"},

    {"id": "minimax", "name": "MiniMax", "icon": "minimax.svg", "category": ["chat"], "prefix": "minimax",
     "api_base": "https://api.minimax.chat/v1"},

    {"id": "hunyuan", "name": "腾讯混元", "icon": "hunyuan.svg", "category": ["chat"], "prefix": "tencent",
     "api_base": "https://api.hunyuan.cloud.tencent.com/v1"},

    {"id": "baidu", "name": "百度千帆", "icon": "baidu.svg", "category": ["chat"], "prefix": "openai_like",
     "api_base": "https://qianfan.baidubce.com/v2",
     "note": "litellm 未收录百度价格，需在 custom_pricing 配置价格才能计费"},

    {"id": "iflytek", "name": "讯飞星火（OpenAI 兼容）", "icon": "iflytek.svg", "category": ["chat"], "prefix": "openai_like",
     "api_base": "https://spark-api-open.xf-yun.com/v1",
     "note": "litellm 未收录讯飞价格，需在 custom_pricing 配置价格才能计费"},

    {"id": "mistral", "name": "Mistral", "icon": "mistral.svg", "category": ["chat"], "prefix": "mistral",
     "api_base": "https://api.mistral.ai/v1"},

    {"id": "groq", "name": "Groq", "icon": "groq.svg", "category": ["chat"], "prefix": "groq",
     "api_base": "https://api.groq.com/openai/v1"},

    {"id": "together", "name": "Together AI", "icon": "together_ai.svg", "category": ["chat"], "prefix": "together_ai",
     "api_base": "https://api.together.xyz/v1"},

    {"id": "openrouter", "name": "OpenRouter", "icon": "openrouter.svg", "category": ["chat"], "prefix": "openrouter",
     "api_base": "https://openrouter.ai/api/v1"},

    {"id": "perplexity", "name": "Perplexity", "icon": "perplexity.svg", "category": ["chat"], "prefix": "perplexity",
     "api_base": "https://api.perplexity.ai"},

    {"id": "xai", "name": "xAI Grok", "icon": "xai.svg", "category": ["chat"], "prefix": "xai",
     "api_base": "https://api.x.ai/v1"},

    {"id": "azure", "name": "Azure OpenAI", "icon": "azure.svg", "category": ["chat", "tts", "embedding"], "prefix": "azure",
     "api_base": "https://RESOURCE.openai.azure.com"},

    {"id": "bedrock", "name": "AWS Bedrock", "icon": "bedrock.svg", "category": ["chat", "embedding"], "prefix": "bedrock",
     "api_base": ""},

    {"id": "lm_studio", "name": "LM Studio（本地）", "icon": "lmstudio.svg", "category": ["chat"], "prefix": "lm_studio",
     "api_base": "http://localhost:1234/v1"},
    {"id": "xiaomi", "name": "小米 MiMo", "icon": "xiaomi.svg", "category": ["chat", "embedding"], "prefix": "xiaomi_mimo",
     "api_base": "https://api.xiaomimimo.com/v1",
     "note": "litellm 价格表未收录，需在 custom_pricing 配置价格才能计费"},
]


def list_vendors() -> list[dict]:
    """面板展示用厂商清单"""
    return list(VENDORS)


# ═══════════════════════════ Provider 主类 ═══════════════════════════


@register_provider("litellm")
class LiteLLMProvider(BaseProvider):
    name = "litellm"

    def __init__(self, config: dict):
        super().__init__(config)
        self._timeout = config.get("timeout", 60)
        self._max_retries = config.get("max_retries", 3)
        self._strip_think = config.get("strip_think", True)
        self._default_model = config.get("model", "") or ""
        self._custom_models = config.get("custom_models", []) or []
        self._model_prefix = config.get("model_prefix", "")
        self._custom_pricing = config.get("custom_pricing", {}) or {}
        self.models = [m for m in ([self._default_model] + self._custom_models) if m]

    async def open(self):
        await super().open()
        litellm.drop_params = True
        self._register_pricing()

    def _register_pricing(self) -> None:
        """注册自定义模型价格（litellm 官方未收录的厂商，如硅基流动）

        custom_pricing 格式（价格按"元/百万 token"填写，与厂商官网一致）:
            {模型名: {"input": 0.35, "output": 1.4, "max_tokens": 32768}}
        注册时换算成美元/token（litellm 计价表单位）。
        """
        if not self._custom_pricing:
            return
        from loyan.brain.provider.monitor.cost import yuan_per_million_to_usd_per_token
        cost_map = {}
        for model, price in self._custom_pricing.items():
            full = self._full_model(model)
            cost_map[full] = {
                "input_cost_per_token": yuan_per_million_to_usd_per_token(float(price.get("input", 0))),
                "output_cost_per_token": yuan_per_million_to_usd_per_token(float(price.get("output", 0))),
                "max_tokens": int(price.get("max_tokens", 32768)),
            }
        try:
            litellm.register_model(cost_map)
        except Exception as e:
            _logger.warning("register custom pricing failed: %s", e)

    def _full_model(self, model: str) -> str:
        if not self._model_prefix:
            return model
        if self._model_prefix == "openai_like":
            return f"openai/{model}"
        if "/" not in model:
            return f"{self._model_prefix}/{model}"
        return model

    def _common_kwargs(self, **extra) -> dict:
        kwargs = {"timeout": self._timeout, "num_retries": self._max_retries, **extra}
        if self.api_base:
            kwargs["api_base"] = self.api_base
        return kwargs

    def _api_keys(self) -> list:
        """多 key：逗号分隔，最左优先，失败依次右移"""
        if not self.api_key:
            return []
        return [k.strip() for k in self.api_key.split(",") if k.strip()]

    def _classify_error(self, e: Exception) -> Exception:
        if isinstance(e, LiteLLMAuthError):
            return AuthError("API Key 无效或已过期，请在面板中重新配置")
        if isinstance(e, LiteLLMRateLimit):
            return RateLimitError("请求过于频繁，请稍后重试")
        if isinstance(e, LiteLLMTimeout):
            return TimeoutError("请求超时，请检查网络或 API 地址")
        if isinstance(e, ContextWindowExceededError):
            return ModelNotAvailableError(f"{'请求参数错误'}: context window exceeded")
        if isinstance(e, LiteLLMNotFound):
            return ModelNotAvailableError("模型不存在或已下线")
        if isinstance(e, LiteLLMBadRequest):
            return ProviderNotAvailableError(f"{'请求参数错误'}: {e}")
        if isinstance(e, LiteLLMAPIError):
            status = getattr(e, "status_code", 0) or 0
            if status == 429:
                return QuotaExceededError("额度耗尽或请求频率过高")
            return ProviderNotAvailableError(f"HTTP {status}")
        if isinstance(e, (AuthError, RateLimitError, TimeoutError, ModelNotAvailableError,
                          ProviderNotAvailableError, QuotaExceededError)):
            return e
        return ProviderNotAvailableError(str(e))

    async def chat(self, messages: list, model: str, **kwargs) -> dict:
        msgs = normalize_messages(messages)
        start = time.time()
        strip = kwargs.pop("strip_think", self._strip_think)
        keys = self._api_keys()
        last_err: Exception | None = None
        for key in keys or [None]:
            try:
                kwargs_ = self._common_kwargs(**kwargs)
                kwargs_.setdefault("max_tokens", max_output_tokens(self._full_model(model)))
                if key:
                    kwargs_["api_key"] = key
                resp = await litellm.acompletion(
                    model=self._full_model(model),
                    messages=msgs,
                    **kwargs_,
                )
                content = resp.choices[0].message.content or ""
                if strip:
                    content = strip_think_block(content)
                return {
                    "content": content,
                    "model": getattr(resp, "model", None) or model,
                    "usage": normalize_usage(getattr(resp, "usage", None)),
                    "time": round(time.time() - start, 2),
                }
            except Exception as e:
                last_err = e
                if key:
                    _logger.warning("api_key %s... failed: %s", key[:8], e)
                elif len(keys) > 1:
                    _logger.warning("request failed: %s", e)
        raise self._classify_error(last_err)

    async def chat_stream(self, messages: list, model: str, **kwargs) -> AsyncIterator[dict]:
        msgs = normalize_messages(messages)
        start = time.time()
        strip = kwargs.pop("strip_think", self._strip_think)
        think = ThinkStrip(remove=strip, emit_reasoning=not strip)
        tool_buf = ToolCallBuffer()
        done_sent = False
        keys = self._api_keys()
        resp = None
        last_err: Exception | None = None
        for key in keys or [None]:
            try:
                kwargs_ = self._common_kwargs(**kwargs)
                kwargs_["timeout"] = kwargs.get("timeout", 600)
                kwargs_.setdefault("max_tokens", max_output_tokens(self._full_model(model)))
                if key:
                    kwargs_["api_key"] = key
                resp = await litellm.acompletion(
                    model=self._full_model(model),
                    messages=msgs,
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs_,
                )
                break
            except Exception as e:
                last_err = e
                if key:
                    _logger.warning("api_key %s... stream failed: %s", key[:8], e)
        if resp is None:
            raise self._classify_error(last_err)
        try:
            async for chunk in resp:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    text = getattr(delta, "content", None)
                    if text:
                        for kind, piece in think.feed(text):
                            yield {"type": kind, "content": piece}
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning and not strip:
                        yield {"type": "reasoning", "content": reasoning}
                    tool_calls = getattr(delta, "tool_calls", None)
                    if tool_calls:
                        tool_buf.feed(tool_calls)
                usage = getattr(chunk, "usage", None)
                if usage is not None and not done_sent:
                    tail = think.flush()
                    if tail:
                        yield {"type": tail[0], "content": tail[1]}
                    yield {
                        "type": "done",
                        "usage": normalize_usage(usage),
                        "time": round(time.time() - start, 2),
                    }
                    done_sent = True
            if not done_sent:
                tail = think.flush()
                if tail:
                    yield {"type": tail[0], "content": tail[1]}
                yield {"type": "done", "usage": {"prompt": 0, "completion": 0, "total": 0},
                       "time": round(time.time() - start, 2)}
        except Exception as e:
            raise self._classify_error(e)

    async def embedding(self, texts: list, model: str, **kwargs) -> list:
        resp = await litellm.aembedding(
            model=self._full_model(model),
            input=texts,
            **self._common_kwargs(**kwargs),
        )
        return [d.embedding for d in resp.data]

    async def list_models(self) -> list[str]:
        models = set(self._custom_models)
        try:
            for key in litellm.model_cost:
                prefix, _, name = key.partition("/")
                if name and (not self._model_prefix or prefix == self._model_prefix):
                    models.add(name if self._model_prefix else key)
        except Exception:
            pass
        return sorted(models)

    def supports_tools(self, model: str) -> bool:
        return supports_tools(self._full_model(model))

    def supports_vision(self, model: str) -> bool:
        return supports_vision(self._full_model(model))

    def model_context_length(self, model: str) -> int:
        return context_length(self._full_model(model))

    def is_reasoning_model(self, model: str) -> bool:
        return is_reasoning_model(self._full_model(model))
