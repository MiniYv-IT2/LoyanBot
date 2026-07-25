"""带超时控制、错误隔离和统计信息的钩子执行器"""

import asyncio
import time
import logging
from typing import Optional

from .events import LifecycleEvent, startup_events, shutdown_events, event_label
from .registry import HookRegistry, HookEntry
from ..state.errors import HookTimeoutError, HookExecutionError

_logger = logging.getLogger("Core.Lifecycle.Hooks.Executor")


class HookExecutor:
    def __init__(self, registry: HookRegistry):
        self._registry = registry
        self._results: dict[str, list[dict]] = {}

    async def run_event(
        self,
        event: LifecycleEvent,
        context: Optional[dict] = None,
        fail_fast: bool = False,
        parallel: bool = False,
        max_concurrent: int = 0,
    ) -> list[dict]:
        hooks = self._registry.get_by_event(event)
        if not hooks:
            _logger.debug("Event %s: no hooks registered", event.value)
            return []

        _logger.info(
            "Running event %s (%d hooks, parallel=%s)",
            event.value, len(hooks), parallel,
        )
        results = []
        ctx = context or {}

        if parallel:
            sem = asyncio.Semaphore(max_concurrent) if max_concurrent > 0 else None
            async def _run_with_sem(entry):
                if sem:
                    async with sem:
                        return await self._run_single(entry, ctx)
                return await self._run_single(entry, ctx)
            tasks = [_run_with_sem(e) for e in hooks]
            completed = await asyncio.gather(*tasks)
            results = list(completed)
            if fail_fast:
                for r in results:
                    if not r["success"]:
                        _logger.warning(
                            "Fail-fast triggered at hook '%s' for event %s",
                            r["hook"], event.value,
                        )
                        break
        else:
            for entry in hooks:
                result = await self._run_single(entry, ctx)
                results.append(result)
                if fail_fast and not result["success"]:
                    _logger.warning(
                        "Fail-fast triggered at hook '%s' for event %s",
                        entry.name, event.value,
                    )
                    break

        self._results.setdefault(event.value, []).extend(results)
        ok = sum(1 for r in results if r["success"])
        failed = len(results) - ok
        if failed:
            _logger.warning(
                "Event %s: %d/%d hooks succeeded, %d failed",
                event.value, ok, len(results), failed,
            )
        else:
            _logger.info(
                "Event %s: all %d hooks completed",
                event.value, len(results),
            )
        return results

    async def run_startup(
        self,
        context: Optional[dict] = None,
        fail_fast: bool = False,
    ) -> dict[str, list[dict]]:
        _logger.info("Running startup event sequence")
        results = {}
        for event in startup_events():
            res = await self.run_event(event, context, fail_fast)
            results[event.value] = res
        return results

    async def run_shutdown(
        self,
        context: Optional[dict] = None,
        fail_fast: bool = False,
    ) -> dict[str, list[dict]]:
        _logger.info("Running shutdown event sequence")
        results = {}
        for event in shutdown_events():
            res = await self.run_event(event, context, fail_fast)
            results[event.value] = res
        return results

    async def _run_single(
        self,
        entry: HookEntry,
        context: dict,
    ) -> dict:
        start = time.time()
        label = f"{entry.name}@{entry.event.value}"
        try:
            await asyncio.wait_for(
                entry.callback(context),
                timeout=entry.timeout,
            )
            elapsed = round(time.time() - start, 4)
            entry.call_count += 1
            entry.last_duration = elapsed
            _logger.debug(
                "Hook OK: %s  duration=%.4fs", label, elapsed,
            )
            return {
                "hook": entry.name,
                "event": entry.event.value,
                "success": True,
                "duration": elapsed,
                "error": None,
            }
        except asyncio.TimeoutError:
            elapsed = round(time.time() - start, 4)
            entry.fail_count += 1
            entry.last_error = f"timeout after {entry.timeout}s"
            err = HookTimeoutError(entry.name, entry.event.value, entry.timeout)
            _logger.error("Hook TIMEOUT: %s  timeout=%ds", label, entry.timeout)
            return {
                "hook": entry.name,
                "event": entry.event.value,
                "success": False,
                "duration": elapsed,
                "error": str(err),
            }
        except Exception as e:
            elapsed = round(time.time() - start, 4)
            entry.fail_count += 1
            entry.last_error = str(e)
            wrapped = HookExecutionError(entry.name, entry.event.value, e)
            _logger.error(
                "Hook FAILED: %s  duration=%.4fs  error=%s",
                label, elapsed, e,
            )
            return {
                "hook": entry.name,
                "event": entry.event.value,
                "success": False,
                "duration": elapsed,
                "error": str(wrapped),
            }

    def results(self, event: Optional[LifecycleEvent] = None) -> dict:
        if event:
            return {event.value: self._results.get(event.value, [])}
        return dict(self._results)

    def clear_results(self):
        self._results.clear()
        _logger.debug("Executor results cleared")
