"""组件健康检查框架"""

import logging
from typing import Optional

_logger = logging.getLogger("Core.Lifecycle.Health.Checker")


class HealthCheck:
    def __init__(self, name: str):
        self._name = name
        self._last_result: Optional[dict] = None
        self._consecutive_failures: int = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def last_result(self) -> Optional[dict]:
        return self._last_result

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    async def check(self) -> dict:
        try:
            result = await self._run()
            self._last_result = result
            if result.get("ok", False):
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
            return result
        except Exception as e:
            self._consecutive_failures += 1
            self._last_result = {"ok": False, "error": str(e)}
            _logger.warning("Health check '%s' failed: %s", self._name, e)
            return self._last_result

    async def _run(self) -> dict:
        raise NotImplementedError


class LambdaCheck(HealthCheck):
    def __init__(self, name: str, fn: callable):
        super().__init__(name)
        self._fn = fn

    async def _run(self) -> dict:
        result = self._fn()
        if isinstance(result, dict):
            return result
        return {"ok": bool(result), "detail": str(result)}


class CompositeChecker:
    def __init__(self):
        self._checks: dict[str, HealthCheck] = {}

    def add(self, check: HealthCheck):
        self._checks[check.name] = check

    def remove(self, name: str):
        self._checks.pop(name, None)

    def add_lambda(self, name: str, fn: callable) -> LambdaCheck:
        c = LambdaCheck(name, fn)
        self.add(c)
        return c

    def get(self, name: str) -> Optional[HealthCheck]:
        return self._checks.get(name)

    async def run_all(self) -> dict[str, dict]:
        results = {}
        for name, check in self._checks.items():
            results[name] = await check.check()
        ok = sum(1 for r in results.values() if r.get("ok"))
        _logger.debug(
            "Health checks: %d/%d passed", ok, len(results),
        )
        return results

    async def run_one(self, name: str) -> Optional[dict]:
        check = self._checks.get(name)
        if not check:
            return None
        return await check.check()

    def summary(self) -> dict:
        return {
            "checks": list(self._checks.keys()),
            "count": len(self._checks),
        }

    def clear(self):
        self._checks.clear()
