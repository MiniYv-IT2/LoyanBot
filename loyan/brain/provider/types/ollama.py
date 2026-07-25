"""Ollama 本地模型提供商"""

import json
import logging

import httpx

from loyan.brain.provider.base import BaseProvider, register_provider
from loyan.i18n import t
from loyan.brain.provider.errors import ProviderNotAvailableError

_logger = logging.getLogger("Brain.provider.ollama")


@register_provider("ollama")
class OllamaProvider(BaseProvider):
    name = "ollama"
    models = []

    async def open(self):
        await super().open()
        self._api_base = self._api_base or "http://localhost:11434"
        proxy = self.config.get("proxy", "")
        kwargs = {"base_url": self._api_base, "timeout": 60}
        if proxy:
            kwargs["proxies"] = proxy
        self._client = httpx.AsyncClient(**kwargs)
        _logger.info(f"Ollama 客户端已初始化")

    async def close(self):
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    async def chat(self, messages: list, model: str, **kwargs) -> str:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            resp = await self._client.post("/api/chat", json={
                "model": model, "messages": messages, "stream": False, **kwargs
            })
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            _logger.error(f"Ollama chat 失败: {e}")
            raise

    async def chat_stream(self, messages: list, model: str, **kwargs):
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            async with self._client.stream("POST", "/api/chat", json={
                "model": model, "messages": messages, "stream": True, **kwargs
            }) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
        except Exception as e:
            _logger.error(f"Ollama stream 失败: {e}")
            raise

    async def list_models(self) -> list[str]:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            _logger.error(f"Ollama 获取模型列表失败: {e}")
            return self.models
