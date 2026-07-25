"""OpenAI / OpenAI 兼容 API 提供商。

chat() 返回:
    {"content": str, "model": str, "usage": {...}, "time": float}

chat_stream() 产出:
    {"type": "text", "content": str}
    {"type": "done", "usage": {...}, "time": float}
"""

import base64
import logging
import os
import time
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError as OpenAIRateLimit
from openai.types.chat import ChatCompletion

from loyan.brain.provider.base import BaseProvider, register_provider
from loyan.brain.provider.errors import (
    AuthError,
    ProviderNotAvailableError,
    RateLimitError,
    TimeoutError,
)
from loyan.i18n import t

_logger = logging.getLogger("Brain.provider.openai")


@register_provider("openai")
class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, config: dict):
        super().__init__(config)
        self._timeout = config.get("timeout", 60)
        self._max_retries = config.get("max_retries", 3)

    async def open(self):
        await super().open()
        if not self.api_key:
            raise AuthError(f"{self.name}: {t('provider.auth_failed')}")
        http_client = None
        proxy = self.config.get("proxy", "")
        if proxy:
            http_client = httpx.AsyncClient(proxy=proxy, timeout=self._timeout)
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base or "https://api.openai.com/v1",
            timeout=self._timeout,
            max_retries=self._max_retries,
            http_client=http_client,
        )
        _logger.info(f"客户端已初始化: {self.api_base}")

    def _resolve_image(self, value: Any) -> dict:
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
            return {"type": "image_url", "image_url": {"url": url}}
        return {"type": "text", "text": str(value)}

    def _normalize_messages(self, messages: list) -> list:
        out = []
        for msg in messages:
            images = msg.pop("images", None) or msg.pop("image_urls", None)
            if not images:
                out.append(msg)
                continue
            content = msg.get("content", "")
            parts = []
            if content:
                parts.append({"type": "text", "text": str(content)})
            for img in images:
                parts.append(self._resolve_image(img))
            out.append({"role": msg.get("role", "user"), "content": parts})
        return out

    def _classify_error(self, e: Exception) -> Exception:
        if isinstance(e, OpenAIRateLimit):
            return RateLimitError(t("provider.rate_limited"))
        if isinstance(e, APITimeoutError):
            return TimeoutError(t("provider.timeout"))
        if isinstance(e, APIError):
            code = getattr(e, "status_code", 0)
            body = getattr(e, "body", {}) or {}
            msg = body.get("error", {}).get("message", "") if isinstance(body, dict) else ""
            fallback = {
                400: t("provider.bad_request"),
                401: t("provider.unauthorized"),
                403: t("provider.forbidden"),
                404: t("provider.model_not_found"),
                429: t("provider.quota_exhausted"),
                500: t("provider.server_error"),
                502: t("provider.bad_gateway"),
                503: t("provider.service_unavailable"),
            }
            hint = msg or fallback.get(code, f"HTTP {code}")
            return ProviderNotAvailableError(f"{hint}")
        return e

    async def chat(self, messages: list, model: str, **kwargs) -> dict:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        messages = self._normalize_messages(messages)
        start = time.time()
        try:
            resp: ChatCompletion = await self._client.chat.completions.create(
                model=model, messages=messages, **kwargs,
            )
            usage = resp.usage
            return {
                "content": resp.choices[0].message.content or "",
                "model": resp.model,
                "usage": {
                    "prompt": usage.prompt_tokens if usage else 0,
                    "completion": usage.completion_tokens if usage else 0,
                    "total": usage.total_tokens if usage else 0,
                },
                "time": round(time.time() - start, 2),
            }
        except Exception as e:
            raise self._classify_error(e)

    async def chat_stream(self, messages: list, model: str, **kwargs) -> AsyncIterator[dict]:
        if not self._client:
            raise ProviderNotAvailableError(f"{self.name}: {t('provider.not_initialized')}")
        messages = self._normalize_messages(messages)
        start = time.time()
        try:
            stream = await self._client.chat.completions.create(
                model=model, messages=messages, stream=True,
                stream_options={"include_usage": True}, **kwargs,
            )
            async for chunk in stream:
                choices = chunk.choices
                if choices and choices[0].delta.content:
                    yield {"type": "text", "content": choices[0].delta.content}
                if chunk.usage:
                    u = chunk.usage
                    yield {"type": "done", "usage": {"prompt": u.prompt_tokens or 0, "completion": u.completion_tokens or 0, "total": u.total_tokens or 0}, "time": round(time.time() - start, 2)}
        except Exception as e:
            raise self._classify_error(e)

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
            return sorted([m.id for m in models.data])
        except Exception:
            return []
