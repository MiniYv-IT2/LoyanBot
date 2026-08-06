"""ChatEngine — 对话引擎主入口"""

import logging
import time

from loyan.brain.chat.persona import persona_mgr
from loyan.brain.provider.manager import ProviderManager
from loyan.brain.provider.errors import ProviderError

_logger = logging.getLogger("Brain.chat")


class ChatEngine:
    def __init__(self, provider_mgr: ProviderManager):
        self.providers = provider_mgr

    async def _build_messages(self, message: str, persona: str = "", session_id: str = "") -> list:
        prompt = ""
        if persona:
            p = await persona_mgr.get(persona)
            if p:
                prompt = p.prompt
        if not prompt:
            prompt = await persona_mgr.current_prompt()
        msgs = []
        if prompt:
            msgs.append({"role": "system", "content": prompt})
        if session_id:
            loaded = False
            try:
                from loyan.core.db_manager import get_db
                db = await get_db("chat_sessions")
                table = "im_messages" if session_id.startswith("chat_") and not session_id.startswith("chat_panel_web_") else "messages"
                rows = await db.fetchall(
                    f"SELECT role, content FROM {table} WHERE session_id = ? AND role IN ('user','assistant') ORDER BY id",
                    session_id)
                for role, content in rows:
                    if content:
                        msgs.append({"role": role, "content": content})
                loaded = bool(rows)
            except Exception:
                pass
            if loaded:
                return msgs
        msgs.append({"role": "user", "content": message})
        return msgs

    async def chat(
        self,
        message: str,
        session_id: str = "",
        model: str = "",
        provider: str = "",
        **kwargs,
    ) -> str:
        """发送消息，返回完整回复"""
        from loyan.brain.provider.monitor.stats import stats
        inst_id, prov = self.providers.resolve(provider)
        if not prov:
            return " " + "没有可用的模型提供商"

        model = model or (prov.models[0] if prov.models else "")
        if not model:
            return " " + "未指定模型"

        messages = await self._build_messages(message)
        start = time.time()

        try:
            reply = await prov.chat(messages, model, **kwargs)
            latency = round(time.time() - start, 2)
            usage = reply.get("usage", {}) if isinstance(reply, dict) else {}
            try:
                await stats.record(inst_id, model, usage, latency, True)
            except Exception:
                pass
            if isinstance(reply, dict):
                return reply.get("content", "") or ""
            return reply or ""
        except ProviderError as e:
            try:
                await stats.record(inst_id, model, {}, round(time.time() - start, 2), False)
            except Exception:
                pass
            _logger.error(f"对话失败 [{provider}/{model}]: {e}")
            return f" {e}"
        except Exception as e:
            _logger.error(f"对话异常 [{provider}/{model}]: {e}")
            return " " + "请求失败，请稍后重试"

    async def chat_stream(
        self,
        message: str,
        session_id: str = "",
        model: str = "",
        provider: str = "",
        persona: str = "",
        **kwargs,
    ):
        """流式对话（面板用）

        产出 dict 事件：
            {"type": "reasoning", "content": str}  思考增量（strip_think=False 时）
            {"type": "text", "content": str}        正文增量
            {"type": "done", "usage": {...}, "time": float}
        """
        from loyan.brain.provider.monitor.stats import stats
        inst_id, prov = self.providers.resolve(provider)
        if not prov:
            yield {"type": "text", "content": "没有可用的模型提供商"}
            return

        model = model or (prov.models[0] if prov.models else "")
        if not model:
            yield {"type": "text", "content": "未指定模型"}
            return

        messages = await self._build_messages(message, persona, session_id)
        start = time.time()
        try:
            async for chunk in prov.chat_stream(messages, model, **kwargs):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "done":
                        try:
                            await stats.record(inst_id, model, chunk.get("usage", {}),
                                               chunk.get("time", 0), True)
                        except Exception:
                            pass
                    yield chunk
                else:
                    yield {"type": "text", "content": str(chunk)}
        except ProviderError as e:
            try:
                await stats.record(inst_id, model, {}, round(time.time() - start, 2), False)
            except Exception:
                pass
            _logger.error(f"流式对话失败 [{provider}/{model}]: {e}")
            yield {"type": "text", "content": f" {e}"}
        except Exception as e:
            _logger.error(f"流式对话异常 [{provider}/{model}]: {e}")
            yield {"type": "text", "content": "请求失败，请稍后重试"}
