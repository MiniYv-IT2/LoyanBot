"""熔断器 — 连续失败后暂时跳过该提供商"""

import logging
import time

from loyan.i18n import t

_logger = logging.getLogger("Brain.router.circuit")

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, cooldown: float = 60.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self._state = STATE_CLOSED
        self._failures = 0
        self._last_failure = 0.0

    @property
    def state(self) -> str:
        if self._state == STATE_OPEN and time.time() - self._last_failure > self.cooldown:
            self._state = STATE_HALF_OPEN
            _logger.info(f"[{self.name}] {t('router.half_open')}")
        return self._state

    def call(self, func, *args, **kwargs):
        if self.state == STATE_OPEN:
            raise CircuitBreakerOpenError(t("router.circuit_open_msg", name=self.name))

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def acall(self, func, *args, **kwargs):
        if self.state == STATE_OPEN:
            raise CircuitBreakerOpenError(t("router.circuit_open_msg", name=self.name))

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self._failures = 0
        self._state = STATE_CLOSED

    def _on_failure(self):
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.threshold:
            self._state = STATE_OPEN
            _logger.warning(t("router.circuit_tripped", name=self.name, count=self._failures, cooldown=self.cooldown))
        elif self._state == STATE_HALF_OPEN:
            self._state = STATE_OPEN
            _logger.warning(t("router.circuit_half_open_failed", name=self.name))


class CircuitBreakerOpenError(Exception):
    pass
