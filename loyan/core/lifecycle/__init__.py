"""LoyanBot 全局生命周期管理

一个分阶段、钩子驱动的生命周期系统，用于编排应用的启动、关闭和健康监控，
无需与特定模块紧密耦合。

用法：
    from loyan.core.lifecycle import LifecycleManager, Phase, LifecycleEvent

    mgr = LifecycleManager()
    mgr.register_hook(LifecycleEvent.READY, my_ready_handler)
    await mgr.start()
"""

from .lifecycle_manager import LifecycleManager
from .state import (
    Phase, StateMachine, can_transition,
    forward_range, shutdown_range, get_description,
    LifecycleError, PhaseTransitionError, HookTimeoutError,
    HookExecutionError, ComponentNotReadyError, LifecycleTimeoutError,
    DuplicateHookError,
)
from .hooks import (
    LifecycleEvent, HookRegistry, HookEntry, HookExecutor,
    startup_events, shutdown_events,
)
from .health import (
    MetricsCollector, HealthReporter, HealthCheck, LambdaCheck, CompositeChecker,
)


# ── 全局单例（模块间共享同一个生命周期实例） ──
lifecycle = LifecycleManager()
