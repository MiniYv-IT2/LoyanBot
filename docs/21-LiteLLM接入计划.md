# LiteLLM 统一接入设计（临时计划表，非官方文档）

> 目标：用 LiteLLM 统一所有大模型提供商，替换现有 4 个私有适配器。
> 状态：调研完成，待实施。基于 LiteLLM 官方 API 文档（docs.litellm.ai）设计。

## LiteLLM 能做什么（官方 API 能力）

**统一入口**：`completion()` / `acompletion()` 一个接口调 100+ 厂商，输出统一 OpenAI 格式。

| API | 能力 |
|---|---|
| `completion(model, messages, **kw)` | 非流式对话，`model="deepseek/deepseek-chat"` 前缀即厂商 |
| `acompletion()` | 异步版本（我们全异步，用这个） |
| `stream=True` / `stream_options` | 流式输出，async for chunk 迭代 |
| `tools=` + `tool_choice` | 函数调用，`supports_function_calling()` 探测能力 |
| `response_format` | 结构化输出：`json_object` / Pydantic json_schema |
| `litellm.get_supported_openai_params(model)` | 查模型支持哪些参数（temperature/max_tokens/...） |
| `litellm.model_cost_map` | 内置价格表，`response_cost` 直接给本次花费 |
| `litellm.token_counter` | token 计数 |
| `litellm.Router` | 多模型负载均衡 / fallback / 重试 / cooldown |
| 统一异常 | `AuthenticationError` / `RateLimitError` / `ContextWindowExceededError` / `APIError` 等 |
| 环境变量 | `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / ... 或 `api_key=` 参数 |

**关键优势（免填 URL）**：LiteLLM 内置每个厂商的默认 `api_base`。
用户只需 `model="deepseek/deepseek-chat"` + api_key，**URL 完全不填**。
自建网关（如 one-api）才需要 `api_base` 覆盖——作为高级可选项。

## 我们的封装层（brain 内新增/改造，几千行）

### 1. 统一 Provider（新增 `types/litellm.py`，~600 行）

继承现有 `BaseProvider`，实现三个抽象方法 + 扩展：

- `chat(messages, model)` → `await acompletion()`，返回文本
- `chat_stream(messages, model)` → async generator
- `list_models()` → 按厂商前缀过滤 `litellm.model_cost_map`
- 参数透传：`temperature` / `max_tokens` / `top_p` 等由配置注入
- 异常映射：litellm 统一异常 → `ProviderError`（带 i18n 消息）
- usage/cost 采集：`response.usage` + `response_cost` → 交给 monitor

### 2. 厂商注册表（新增 `provider/vendors.py`，~200 行）

- 内置厂商列表：`{ "deepseek": "DeepSeek", "openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google Gemini", "ollama": "本地 Ollama", "qwen": "通义千问", "moonshot": "Kimi", ... }`
- 每厂商默认 `api_base` 从 litellm 读（`litellm.get_llm_provider()`），**不手写 URL**
- 厂商 → 推荐模型列表（下拉用）

### 3. schema 前端渲染（新增 `provider/source/litellm.schema_conf.json` + i18n，~150 行）

前端（面板 Provider 页）直接渲染表单，字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `provider` | select | 厂商下拉（来自注册表），选完自动带出默认 URL |
| `model` | str/select | 模型名（下拉推荐 + 可手输） |
| `api_key` | str secret | API Key，keystore 加密存储 |
| `api_base` | str 可选 | **默认留空**，自建网关才填 |
| `temperature` | float 可选 | 默认 0.7 |
| `max_tokens` | int 可选 | 默认空（模型默认） |
| `timeout` | int | 默认 60 |
| `proxy` | str 可选 | 代理地址 |

### 4. InstanceManager 改造（~100 行）

- 表结构：`type` 固定为 litellm，加 `provider`（厂商）、`model`、`extra`（json 存 temperature/max_tokens/proxy）
- 迁移：现有 openai/anthropic/ollama/iflytek 4 类实例 → provider 字段映射
- api_key 加密逻辑不动（已有）

### 5. manager.py 改造（~100 行）

- 删按类型分发（`_registry` 只剩 litellm 一个）
- `load_all()`：读实例 → 构造 LiteLLMProvider → 注入厂商/模型
- 兼容保留 `provider.type` 读取

### 6. cost 监控改造（~80 行）

- 现有 `monitor/cost.py` 改为消费 litellm 的 `usage` + `response_cost`
- 删除手写价格表

### 7. 对话链路（ChatEngine 微调，~50 行）

- `_build_messages` 已符合 OpenAI 格式，不动
- `chat()` / `chat_stream()` 签名保持，透传 kwargs
- session_id 预留（上下文管理后续接）

## 行数预估

| 模块 | 新增 | 删除 |
|---|---|---|
| types/litellm.py | ~600 | - |
| provider/vendors.py | ~200 | - |
| schema_conf + i18n | ~150 | - |
| InstanceManager 改造 | ~100 | - |
| manager.py 改造 | ~100 | - |
| monitor/cost.py | ~80 | - |
| ChatEngine | ~50 | - |
| 旧适配器 4 个 | - | ~450 |
| 手写 router (chain/circuit) | - | ~150 |
| **合计** | **~1280 行** | **~600 行** |

净增 ~700 行。要达到"几千行"规模，后续迭代加：上下文管理（~300）、函数调用工具系统（~300）、模型测试/诊断 API（~200）、多模型路由配置（~200）——这些都在 litellm 之上做，不碰各家私有协议。

## 实施顺序

1. `types/litellm.py` + `vendors.py`（核心，先能对话）
2. schema + 前端渲染字段
3. InstanceManager 迁移 + manager 改造
4. 删旧适配器
5. cost 监控
6. 联调 `/chat` 全链路

## 参考（官方文档）

- https://docs.litellm.ai/docs/ — quickstart
- https://docs.litellm.ai/docs/providers — 厂商列表（每个厂商有独立文档页）
- https://docs.litellm.ai/docs/completion/input — completion 参数
- https://docs.litellm.ai/docs/completion/stream — 流式+异步
- https://docs.litellm.ai/docs/completion/function_call — 函数调用
- https://docs.litellm.ai/docs/completion/json_mode — 结构化输出
- https://docs.litellm.ai/docs/routing — Router
