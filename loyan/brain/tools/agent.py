"""LoyanAgent — AI 工具调用执行层: 组装 tools schema → 调 provider → 执行工具 → 结果回填"""

import inspect
import json
import logging
import time

from loyan.brain.provider.errors import ProviderError

_logger = logging.getLogger("Brain.tools")


class LoyanAgent:
    """AI 工具调用执行器: 组装 tools schema → 调 provider → 执行工具 → 结果回填(最多5轮)"""
    MAX_ROUNDS = 5

    def __init__(self, engine):
        self._engine = engine

    @staticmethod
    def _build_tools_schema() -> list:
        from loyan.core.decorators.registration import AI_TOOL_REGISTRY
        schema = []
        for item in AI_TOOL_REGISTRY:
            properties = {}
            required = []
            for key, p in (item.get("params") or {}).items():
                properties[key] = {"type": p.get("type", "string"), "description": p.get("description", "")}
                if p.get("required"):
                    required.append(key)
            schema.append({
                "type": "function",
                "function": {
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "parameters": {"type": "object", "properties": properties, "required": required},
                },
            })
        return schema

    async def _execute_tool(self, tool_name, args, ctx) -> str:
        from loyan.core.decorators.registration import AI_TOOL_REGISTRY
        entry = next((t for t in AI_TOOL_REGISTRY if t["name"] == tool_name), None)
        if not entry:
            return f"tool not found: {tool_name}"
        permission = entry.get("permission", "all")
        if ctx is not None:
            if permission == "admin":
                from loyan.core.pipeline.helpers import is_admin
                if not is_admin(ctx):
                    return "permission denied: this tool requires admin"
            elif permission != "all":
                from loyan.core.decorators.security import check_permission_decorator
                if not await check_permission_decorator(str(ctx.sender_id), permission):
                    return "permission denied: this tool requires admin"
        try:
            result = entry["handler_func"](ctx, **args)
            if inspect.isawaitable(result):
                result = await result
            return str(result) if result is not None else ""
        except Exception as e:
            return f"tool execution failed: {e}"

    async def _run_rounds(self, messages, model, prov, ctx, emit=None):
        schema = self._build_tools_schema()
        tools_enabled = True
        if hasattr(prov, "supports_tools") and not prov.supports_tools(model):
            tools_enabled = False
        content = ""
        usage = {}
        for _ in range(self.MAX_ROUNDS):
            try:
                if tools_enabled:
                    resp = await prov.chat(messages, model, tools=schema)
                else:
                    resp = await prov.chat(messages, model)
            except Exception as e:
                if tools_enabled and "not supported" in str(e).lower():
                    tools_enabled = False
                    resp = await prov.chat(messages, model)
                else:
                    raise
            if isinstance(resp, dict):
                content = resp.get("content", "") or ""
                usage = resp.get("usage", usage)
                calls = resp.get("tool_calls")
            else:
                content = str(resp)
                calls = None
            if not calls:
                return content, usage
            messages.append({"role": "assistant", "content": content, "tool_calls": calls})
            for i, tc in enumerate(calls):
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except Exception:
                    args = {}
                if emit:
                    emit({"type": "tool_call", "name": name, "args": args})
                result = await self._execute_tool(name, args, ctx)
                if emit:
                    emit({"type": "tool_result", "name": name, "result": result})
                messages.append({"role": "tool", "tool_call_id": tc.get("id") or f"call_{i}", "content": result})
        return content, usage

    async def chat_with_tools(self, message, session_id="", persona="", provider="", ctx=None, **kwargs) -> str:
        from loyan.brain.provider.monitor.stats import stats
        inst_id, prov = self._engine.providers.resolve(provider)
        if not prov:
            return " " + "没有可用的模型提供商"
        model = kwargs.pop("model", "") or (prov.models[0] if prov.models else "")
        if not model:
            return " " + "未指定模型"
        messages = await self._engine._build_messages(message, persona, session_id)
        start = time.time()
        try:
            content, usage = await self._run_rounds(messages, model, prov, ctx)
            latency = round(time.time() - start, 2)
            try:
                await stats.record(inst_id, model, usage, latency, True)
            except Exception:
                pass
            return content or ""
        except ProviderError as e:
            try:
                await stats.record(inst_id, model, {}, round(time.time() - start, 2), False)
            except Exception:
                pass
            _logger.error(f"工具对话失败 [{provider}/{model}]: {e}")
            return f" {e}"
        except Exception as e:
            _logger.error(f"工具对话异常 [{provider}/{model}]: {e}")
            return " " + "请求失败，请稍后重试"

    async def chat_stream_with_tools(self, message, session_id="", persona="", provider="", ctx=None, **kwargs):
        from loyan.brain.provider.monitor.stats import stats
        inst_id, prov = self._engine.providers.resolve(provider)
        if not prov:
            yield {"type": "text", "content": "没有可用的模型提供商"}
            return
        model = kwargs.pop("model", "") or (prov.models[0] if prov.models else "")
        if not model:
            yield {"type": "text", "content": "未指定模型"}
            return
        messages = await self._engine._build_messages(message, persona, session_id)
        start = time.time()
        try:
            events = []
            content, usage = await self._run_rounds(messages, model, prov, ctx, emit=events.append)
            for ev in events:
                yield ev
            if content:
                yield {"type": "text", "content": content}
            latency = round(time.time() - start, 2)
            try:
                await stats.record(inst_id, model, usage, latency, True)
            except Exception:
                pass
            yield {"type": "done", "usage": usage, "time": latency}
        except ProviderError as e:
            try:
                await stats.record(inst_id, model, {}, round(time.time() - start, 2), False)
            except Exception:
                pass
            _logger.error(f"工具流式对话失败 [{provider}/{model}]: {e}")
            yield {"type": "text", "content": f" {e}"}
        except Exception as e:
            _logger.error(f"工具流式对话异常 [{provider}/{model}]: {e}")
            yield {"type": "text", "content": "请求失败，请稍后重试"}
