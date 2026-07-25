"""Anthropic Claude API 提供商"""

import logging
from typing import Any, AsyncIterator

import httpx
from anthropic import AsyncAnthropic

from loyan.brain.provider.base import BaseProvider, register_provider
from loyan.brain.provider.errors import AuthError, ModelNotAvailableError, ProviderNotAvailableError
from loyan.i18n import t

_logger = logging.getLogger("Brain.provider.anthropic")


def _convert_messages(messages: list) -> tuple[list, str]:
    system = ""
    converted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system = content
        elif role in ("user", "assistant"):
            converted.append({"role": role, "content": content})
    return converted, system


@register_provider("anthropic")
class AnthropicProvider(BaseProvider):
    name = "anthropic"
    models = [
        "claude-sonnet-4-20250514",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]

    async def open(self):
        await super().open()
        if not self.api_key:
            raise AuthError(f"{self.name}: {t('provider.api_key_not_configured')}")
        http_client = None
        proxy = self.config.get("proxy", "")
        if proxy:
            http_client = httpx.AsyncClient(proxy=proxy, timeout=60)
        self._client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.api_base or "https://api.anthropic.com/v1",
            http_client=http_client,
        )
        _logger.info("Anthropic 客户端已初始化")

    async def chat(self, messages: list, model: str, **kwargs) -> str:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            messages, system = _convert_messages(messages)
            kwargs.setdefault("max_tokens", 4096)
            resp = await self._client.messages.create(
                model=model,
                messages=messages,
                system=system or None,
                **kwargs,
            )
            return resp.content[0].text or ""
        except Exception as e:
            _logger.error(f"Anthropic chat 失败: {e}")
            raise

    async def chat_stream(self, messages: list, model: str, **kwargs) -> AsyncIterator[str]:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            messages, system = _convert_messages(messages)
            kwargs.setdefault("max_tokens", 4096)
            async with self._client.messages.stream(
                model=model,
                messages=messages,
                system=system or None,
                **kwargs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            _logger.error(f"Anthropic stream 失败: {e}")
            raise

    async def list_models(self) -> list[str]:
        return self.models
