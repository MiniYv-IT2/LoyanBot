"""讯飞星火 iFlytek Spark 提供商（自定义 HTTP API，非 OpenAI 兼容）"""

import json
import logging
from typing import Any, AsyncIterator

import httpx

from loyan.brain.provider.base import BaseProvider, register_provider
from loyan.i18n import t
from loyan.brain.provider.errors import AuthError, ProviderNotAvailableError
from loyan.brain.provider.keystore import keystore

_logger = logging.getLogger("Brain.provider.iflytek")

DEFAULT_BASE = "https://spark-api.xf-yun.com/v3.5/chat"


@register_provider("iflytek")
class IflytekProvider(BaseProvider):
    name = "iflytek"
    models = ["spark-3.5", "spark-4.0"]

    def __init__(self, config: dict):
        super().__init__(config)
        self._appid: str = ""
        self._api_key: str = ""
        self._api_secret: str = ""

    async def open(self):
        await super().open()
        creds = self._api_key
        if not creds:
            creds = await keystore.get(f"{self.name}.api_key") or ""
        if not creds:
            raise AuthError(f"{self.name}: {t('provider.credential_not_configured')}")
        parts = creds.split("|", 2)
        if len(parts) != 3:
            raise AuthError(f"{self.name}: {t('provider.credential_format_error')}")
        self._appid, self._api_key, self._api_secret = parts
        proxy = self.config.get("proxy", "")
        kwargs = {"base_url": self.api_base or DEFAULT_BASE, "timeout": 60}
        if proxy:
            kwargs["proxies"] = proxy
        self._client = httpx.AsyncClient(**kwargs)
        _logger.info(f"iFlytek 客户端已初始化")

    async def close(self):
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    def _build_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-appid": self._appid,
            "x-apikey": self._api_key,
            "x-apisecret": self._api_secret,
        }

    def _build_body(self, messages: list, model: str, stream: bool = False, **kwargs) -> dict:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if kwargs:
            body.update(kwargs)
        return body

    async def chat(self, messages: list, model: str = "spark-3.5", **kwargs) -> str:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            resp = await self._client.post(
                "",
                headers=self._build_headers(),
                json=self._build_body(messages, model, stream=False, **kwargs),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            _logger.error(f"iFlytek chat 失败: {e}")
            raise

    async def chat_stream(self, messages: list, model: str = "spark-3.5", **kwargs) -> AsyncIterator[str]:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            async with self._client.stream(
                "POST",
                "",
                headers=self._build_headers(),
                json=self._build_body(messages, model, stream=True, **kwargs),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data_str)
                            content = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            _logger.error(f"iFlytek stream 失败: {e}")
            raise

    async def list_models(self) -> list[str]:
        return self.models
