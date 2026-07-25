"""故障切换 — 按优先级依次尝试，一个失败切下一个"""

import logging
from typing import Any, Optional

from loyan.i18n import t
from loyan.brain.provider.manager import ProviderManager
from loyan.brain.provider.router.circuit import CircuitBreaker, CircuitBreakerOpenError

_logger = logging.getLogger("Brain.router.chain")


class FailoverChain:
    def __init__(self, provider_mgr: ProviderManager):
        self._mgr = provider_mgr

    async def execute(
        self,
        providers: list[str],
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        last_error = None
        for name in providers:
            provider = self._mgr.get(name)
            if not provider:
                continue

            cb: Optional[CircuitBreaker] = self._mgr._circuits.get(name)
            try:
                if cb:
                    return await cb.acall(self._call_method, provider, method, *args, **kwargs)
                return await self._call_method(provider, method, *args, **kwargs)
            except CircuitBreakerOpenError:
                _logger.warning(f"[{name}] {t('router.circuit_open')}")
                last_error = t("router.circuit_open_detail", name=name)
                continue
            except Exception as e:
                last_error = f"{name}: {e}"
                _logger.warning(f"[{name}] {t('router.failover')}: {e}")
                continue

        raise RuntimeError(t("router.all_failed", detail=last_error or ""))

    async def _call_method(self, provider, method: str, *args, **kwargs):
        func = getattr(provider, method, None)
        if func is None:
            raise AttributeError(f"{provider.name} {t('router.no_method')} {method}")
        return await func(*args, **kwargs)
