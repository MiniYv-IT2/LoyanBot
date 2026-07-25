"""生命周期异常层次结构"""


class LifecycleError(Exception):
    """所有生命周期错误的基类异常"""


class PhaseTransitionError(LifecycleError):
    """当尝试非法的阶段转换时抛出"""

    def __init__(self, current, target):
        self.current = current
        self.target = target
        super().__init__(f"Illegal transition: {current.name} -> {target.name}")


class HookTimeoutError(LifecycleError):
    """当钩子回调超时时抛出"""

    def __init__(self, hook_name, event, timeout):
        self.hook_name = hook_name
        self.event = event
        self.timeout = timeout
        super().__init__(f"Hook '{hook_name}' timed out after {timeout}s on event {event}")


class HookExecutionError(LifecycleError):
    """包装钩子执行期间引发的异常"""

    def __init__(self, hook_name, event, original):
        self.hook_name = hook_name
        self.event = event
        self.original = original
        super().__init__(f"Hook '{hook_name}' failed on event {event}: {original}")


class ComponentNotReadyError(LifecycleError):
    """在组件阶段到达之前访问时抛出"""

    def __init__(self, component, required_phase, current_phase):
        self.component = component
        self.required_phase = required_phase
        self.current_phase = current_phase
        super().__init__(
            f"Component '{component}' requires phase {required_phase.name}, "
            f"currently at {current_phase.name}"
        )


class LifecycleTimeoutError(LifecycleError):
    """当阶段转换超过总体超时时间时抛出"""


class DuplicateHookError(LifecycleError):
    """当注册具有相同标识的钩子时抛出"""
