"""LifecycleManager — 整个应用生命周期的顶层编排器

将状态机、钩子系统和健康监控整合为单一的异步接口。
模块通过 register_hook() 注册钩子，生命周期模块无需了解具体模块。
提供带有正确阶段排序、超时强制和错误隔离的启动/停止/重启功能。
"""

import asyncio
import logging
import signal
import time
import traceback
from typing import Any, Callable, Optional

from .state import (
    Phase, StateMachine, can_transition, forward_range, shutdown_range,
    LifecycleError, PhaseTransitionError,
)
from .hooks import (
    LifecycleEvent, HookRegistry, HookExecutor,
    startup_events, shutdown_events,
)
from .health import MetricsCollector, HealthReporter, CompositeChecker

_logger = logging.getLogger("Core.Lifecycle")

_DEFAULT_PHASE_TIMEOUT = 120.0
_DEFAULT_HOOK_TIMEOUT = 30.0


class LifecycleManager:
    def __init__(self):
        self._state = StateMachine()
        self._hooks = HookRegistry()
        self._executor = HookExecutor(self._hooks)
        self._metrics = MetricsCollector()
        self._checker = CompositeChecker()
        self._reporter = HealthReporter(
            self._state, self._hooks, self._executor, self._metrics,
        )
        self._phase_events: dict[Phase, asyncio.Event] = {}
        self._phase_timeouts: dict[Phase, float] = {}
        self._running_tasks: list[asyncio.Task] = []
        self._shutdown_requested: bool = False
        self._start_time: float = 0.0
        self._context: dict[str, Any] = {}
        self._on_error_callbacks: list[Callable] = []
        self._auto_restart: bool = False
        self._restart_count: int = 0
        self._max_restarts: int = 3
        self._shutdown_complete: asyncio.Event = asyncio.Event()
        self._shutdown_complete.set()
        self._instance_name: str = "default"

    @property
    def state(self) -> StateMachine:
        return self._state

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    @property
    def executor(self) -> HookExecutor:
        return self._executor

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    @property
    def checker(self) -> CompositeChecker:
        return self._checker

    @property
    def reporter(self) -> HealthReporter:
        return self._reporter

    @property
    def phase(self) -> Phase:
        return self._state.current

    @property
    def is_running(self) -> bool:
        return self._state.is_running

    @property
    def is_shutting_down(self) -> bool:
        return self._state.is_shutting_down

    @property
    def uptime(self) -> float:
        return self._state.uptime

    @property
    def context(self) -> dict:
        return dict(self._context)

    @property
    def restart_count(self) -> int:
        return self._restart_count

    @property
    def instance_name(self) -> str:
        return self._instance_name

    @instance_name.setter
    def instance_name(self, name: str):
        self._instance_name = name

    def set_context(self, key: str, value: Any):
        self._context[key] = value

    def update_context(self, mapping: dict):
        self._context.update(mapping)

    # ── 自动重启配置 ──

    def enable_auto_restart(self, max_restarts: int = 3):
        self._auto_restart = True
        self._max_restarts = max_restarts
        _logger.info("Auto-restart enabled (max=%d)", max_restarts)

    def disable_auto_restart(self):
        self._auto_restart = False
        _logger.info("Auto-restart disabled")

    # ── 错误处理 ──

    def on_error(self, callback: Callable):
        self._on_error_callbacks.append(callback)

    # ── 任务跟踪 ──

    def track_task(self, task: asyncio.Task):
        self._running_tasks.append(task)
        task.add_done_callback(lambda t: self._running_tasks.remove(t) if t in self._running_tasks else None)

    def create_task(self, coro, name: str = "") -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self.track_task(task)
        return task

    # ── 钩子注册快捷方法 ──

    def register_hook(
        self,
        event: LifecycleEvent,
        callback,
        name: str = "",
        priority: int = 50,
        timeout: float = 30.0,
        plugin_name: str = "",
    ):
        return self._hooks.register(event, callback, name, priority, timeout, plugin_name)

    async def fire_event_async(self, event: LifecycleEvent) -> dict:
        return await self._executor.run_event(event)

    def unregister_hook(self, event: LifecycleEvent, callback=None, name: str = ""):
        self._hooks.unregister(event, callback, name)

    def on_phase(self, phase: Phase, callback):
        event = self._phase_to_event(phase)
        if event:
            self.register_hook(event, callback, name=f"on_phase_{phase.name}")

    def set_phase_timeout(self, phase: Phase, timeout: float):
        self._phase_timeouts[phase] = timeout

    # ── 核心生命周期 ──

    async def run(self, stop_timeout: float = 60.0):
        await self.start()
        try:
            await self._shutdown_complete.wait()
        except asyncio.CancelledError:
            _logger.info("Run loop cancelled, shutting down")
        finally:
            await self.stop(timeout=stop_timeout)

    async def start(self, timeout: float = 300.0):
        _logger.info(
            "Starting lifecycle manager [instance=%s]", self._instance_name,
        )
        self._start_time = time.time()
        self._metrics.start_wall_clock()
        self._shutdown_requested = False
        self._shutdown_complete.clear()

        try:
            await asyncio.wait_for(
                self._run_startup_sequence(),
                timeout=timeout,
            )
            elapsed = time.time() - self._start_time
            _logger.info(
                "Lifecycle startup complete in %.2fs [instance=%s]",
                elapsed, self._instance_name,
            )
        except asyncio.TimeoutError:
            _logger.critical(
                "Lifecycle startup timed out after %ds [instance=%s]",
                timeout, self._instance_name,
            )
            self._state.fail(
                self._state.current,
                f"Startup timed out after {timeout}s",
            )
            await self._trigger_error(f"Startup timeout after {timeout}s")
            raise
        except Exception as e:
            _logger.critical(
                "Lifecycle startup failed: %s [instance=%s]",
                e, self._instance_name,
            )
            self._state.fail(self._state.current, str(e))
            await self._trigger_error(str(e))
            raise

    async def stop(self, timeout: float = 60.0):
        _logger.info(
            "Shutting down lifecycle manager [instance=%s]", self._instance_name,
        )
        self._shutdown_requested = True

        try:
            await asyncio.wait_for(
                self._run_shutdown_sequence(),
                timeout=timeout,
            )
            _logger.info(
                "Lifecycle shutdown complete [instance=%s]", self._instance_name,
            )
        except asyncio.TimeoutError:
            _logger.warning(
                "Lifecycle shutdown timed out after %ds [instance=%s]",
                timeout, self._instance_name,
            )
            self._state.transition(Phase.STOPPED)
        except Exception as e:
            _logger.error(
                "Lifecycle shutdown error: %s [instance=%s]",
                e, self._instance_name,
            )
            self._state.transition(Phase.STOPPED)
        finally:
            await self._cancel_running_tasks()
            self._shutdown_complete.set()

    async def restart(self, stop_timeout: float = 60.0, start_timeout: float = 300.0):
        _logger.info(
            "Restarting lifecycle manager [instance=%s] (attempt %d)",
            self._instance_name, self._restart_count + 1,
        )
        self._restart_count += 1
        await self._run_event(LifecycleEvent.ON_RESTART)
        await self.stop(timeout=stop_timeout)
        self._state.reset()
        self._metrics.clear()
        self._executor.clear_results()
        await self.start(timeout=start_timeout)

    async def _cancel_running_tasks(self):
        if not self._running_tasks:
            return
        _logger.debug("Cancelling %d running tasks", len(self._running_tasks))
        for task in self._running_tasks:
            if not task.done():
                task.cancel()
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        self._running_tasks.clear()

    async def _trigger_error(self, message: str):
        await self._run_event(LifecycleEvent.ON_ERROR)
        for cb in self._on_error_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(message)
                else:
                    cb(message)
            except Exception as e:
                _logger.error("Error callback failed: %s", e)

    # ── 阶段等待 ──

    async def wait_for_phase(self, phase: Phase, timeout: Optional[float] = None) -> bool:
        if self._state.current.value >= phase.value:
            return True
        event = self._get_phase_event(phase)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def wait_for_running(self, timeout: Optional[float] = None) -> bool:
        return await self.wait_for_phase(Phase.RUNNING, timeout=timeout)

    async def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        try:
            await asyncio.wait_for(self._shutdown_complete.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    # ── 信号处理 ──

    def install_signal_handlers(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        loop = loop or asyncio.get_event_loop()
        try:
            loop.add_signal_handler(
                signal.SIGINT, lambda: asyncio.create_task(self.stop()),
            )
            loop.add_signal_handler(
                signal.SIGTERM, lambda: asyncio.create_task(self.stop()),
            )
            _logger.debug("Signal handlers installed (SIGINT, SIGTERM)")
        except (NotImplementedError, ValueError) as e:
            _logger.warning("Could not install signal handlers: %s", e)

    # ── 健康检查 ──

    def health_report(self) -> dict:
        return self._reporter.generate()

    def health_text(self) -> str:
        return self._reporter.text_summary()

    def register_check(self, name: str, fn: callable):
        self._reporter.register_check(name, fn)
        self._checker.add_lambda(name, fn)

    # ── 内部：启动序列 ──

    async def _run_startup_sequence(self):
        phases = forward_range()
        _logger.info("Startup sequence: %d phases", len(phases))
        for phase in phases:
            if self._shutdown_requested:
                _logger.warning(
                    "Startup aborted at phase %s [instance=%s]",
                    phase.name, self._instance_name,
                )
                return
            await self._advance_to(phase)

    async def _advance_to(self, target: Phase):
        start = time.time()
        try:
            self._state.transition(target)
            elapsed = round(time.time() - start, 4)
            self._metrics.record_phase(target.name, elapsed, success=True)
        except PhaseTransitionError:
            return

        event = self._phase_to_event(target)
        if event:
            phase_timeout = self._phase_timeouts.get(target, _DEFAULT_HOOK_TIMEOUT)
            event_start = _logger.info(
                "Phase %s: running hooks (timeout=%ds)", target.name, phase_timeout,
            )
            try:
                await asyncio.wait_for(
                    self._run_event(event),
                    timeout=phase_timeout,
                )
            except asyncio.TimeoutError:
                _logger.error(
                    "Phase %s: hooks timed out after %ds", target.name, phase_timeout,
                )
                self._state.fail(target, f"Hooks timed out after {phase_timeout}s")
                await self._trigger_error(f"Phase {target.name} hooks timeout")
                return

        self._notify_phase_waiters(target)
        elapsed = time.time() - start
        _logger.info(
            "Phase %s completed in %.4fs [instance=%s]",
            target.name, elapsed, self._instance_name,
        )

    async def _run_event(self, event: LifecycleEvent, timeout: float = 30.0):
        results = await self._executor.run_event(event, context=self._context)
        for r in results:
            self._metrics.record_hook(
                r["hook"], r["duration"], r["success"],
                meta={"event": event.value},
            )

    def _notify_phase_waiters(self, phase: Phase):
        event = self._phase_events.get(phase)
        if event and not event.is_set():
            event.set()
        # 同时设置所有更早的阶段
        for p, evt in self._phase_events.items():
            if p.value <= phase.value and not evt.is_set():
                evt.set()

    def _get_phase_event(self, phase: Phase) -> asyncio.Event:
        if phase not in self._phase_events:
            self._phase_events[phase] = asyncio.Event()
        return self._phase_events[phase]

    # ── 内部：关闭序列 ──

    async def _run_shutdown_sequence(self):
        _logger.info(
            "Shutdown sequence: running %d phases from %s",
            len(shutdown_range()), self._state.current.name,
        )
        await self._run_event(LifecycleEvent.BEFORE_SHUTDOWN)
        for phase in shutdown_range():
            try:
                self._state.transition(phase)
            except PhaseTransitionError:
                _logger.debug(
                    "Skipping phase %s (current=%s)",
                    phase.name, self._state.current.name,
                )
                continue
        await self._run_event(LifecycleEvent.AFTER_SHUTDOWN)

    # ── 阶段到事件的映射 ──

    @staticmethod
    def _phase_to_event(phase: Phase) -> Optional[LifecycleEvent]:
        mapping = {
            Phase.CONFIG_LOADED: LifecycleEvent.AFTER_CONFIG_LOAD,
            Phase.DATABASE_READY: LifecycleEvent.AFTER_DATABASE_READY,
            Phase.PLUGINS_SCANNED: LifecycleEvent.AFTER_PLUGINS_SCANNED,
            Phase.PLUGINS_LOADED: LifecycleEvent.AFTER_PLUGINS_LOADED,
            Phase.BRAIN_READY: LifecycleEvent.AFTER_BRAIN_READY,
            Phase.INSTANCES_READY: LifecycleEvent.AFTER_INSTANCES_READY,
            Phase.ADAPTERS_READY: LifecycleEvent.AFTER_ADAPTERS_START,
            Phase.RUNNING: LifecycleEvent.READY,
        }
        return mapping.get(phase)

    # ── 诊断信息 ──

    def summary(self) -> dict:
        return {
            "instance": self._instance_name,
            "phase": self._state.current.name,
            "phase_value": self._state.current.value,
            "running": self._state.is_running,
            "uptime": round(self._state.uptime, 2),
            "hooks": self._hooks.count(),
            "tasks": len(self._running_tasks),
            "checks": self._checker.summary(),
            "restart_count": self._restart_count,
            "auto_restart": self._auto_restart,
            "started_at": self._start_time,
        }

    def timeline(self) -> list[dict]:
        return self._metrics.timeline()

    def reset_state(self):
        self._state.reset()
        self._metrics.clear()
        self._executor.clear_results()
        self._running_tasks.clear()
        self._restart_count = 0
        self._shutdown_complete.set()
        _logger.info("Lifecycle manager state reset")

    # ── Async context manager ──

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False

    # ── Auto-save health reports ──

    def enable_auto_health_save(self, directory: str = "storage/health"):
        self._reporter.save_dir = directory
        self._reporter.auto_save = True
        _logger.info("Auto health report save enabled: %s", directory)

    def disable_auto_health_save(self):
        self._reporter.auto_save = False
        _logger.info("Auto health report save disabled")

    def save_health_report(self):
        self._reporter.save()

    def load_health_report(self) -> Optional[dict]:
        return self._reporter.load_latest()

    def list_health_reports(self, max_count: int = 10) -> list[dict]:
        return self._reporter.list_reports(max_count=max_count)

    # ── Periodic health check ──

    async def start_periodic_health_check(self, interval: float = 60.0):
        async def _loop():
            while not self._shutdown_requested:
                await asyncio.sleep(interval)
                try:
                    report = self.health_report()
                    status = report.get("status", "unknown")
                    if status != "healthy":
                        _logger.warning(
                            "Periodic health check: %s  phase=%s",
                            status, report.get("phase", "?"),
                        )
                    _logger.debug(
                        "Periodic health check: %s  uptime=%.1fs",
                        status, report.get("uptime", 0),
                    )
                except Exception as e:
                    _logger.error("Periodic health check failed: %s", e)
        task = self.create_task(_loop(), name="periodic_health_check")
        _logger.info(
            "Periodic health check started (interval=%ds)", interval,
        )
        return task

    # ── Component access helpers ──

    def get_component_status(self, name: str) -> dict:
        report = self.health_report()
        return report.get("components", {}).get(name, {"ok": False, "error": "not found"})

    def is_component_healthy(self, name: str) -> bool:
        status = self.get_component_status(name)
        return status.get("ok", False)
