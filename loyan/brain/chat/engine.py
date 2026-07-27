"""ChatEngine — 对话引擎主入口"""

import logging

from loyan.brain.chat.persona import persona_mgr
from loyan.brain.provider.manager import ProviderManager
from loyan.i18n import t
from loyan.brain.provider.errors import ProviderError

_logger = logging.getLogger("Brain.chat")


class ChatEngine:
    def __init__(self, provider_mgr: ProviderManager):
        self.providers = provider_mgr

    async def _build_messages(self, message: str) -> list:
        prompt = await persona_mgr.current_prompt()
        msgs = []
        if prompt:
            msgs.append({"role": "system", "content": prompt})
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
        prov = self.providers.get(provider)
        if not prov:
            return " " + t("provider.no_providers")

        model = model or (prov.models[0] if prov.models else "")
        if not model:
            return " " + t("provider.no_model")

        messages = await self._build_messages(message)

        try:
            reply = await prov.chat(messages, model, **kwargs)
            if isinstance(reply, dict):
                return reply.get("content", "") or ""
            return reply or ""
        except ProviderError as e:
            _logger.error(f"对话失败 [{provider}/{model}]: {e}")
            return f" {e}"
        except Exception as e:
            _logger.error(f"对话异常 [{provider}/{model}]: {e}")
            return " " + t("chat.request_failed")

    async def chat_stream(
        self,
        message: str,
        session_id: str = "",
        model: str = "",
        provider: str = "",
        **kwargs,
    ):
        """流式对话"""
        prov = self.providers.get(provider)
        if not prov:
            yield " " + t("provider.no_providers")
            return

        model = model or (prov.models[0] if prov.models else "")
        messages = [{"role": "user", "content": message}]

        try:
            async for chunk in prov.chat_stream(messages, model, **kwargs):
                yield chunk
        except ProviderError as e:
            yield f" {e}"
        except Exception as e:
            _logger.error(f"流式对话异常 [{provider}/{model}]: {e}")
            yield " " + t("chat.request_failed_short")
