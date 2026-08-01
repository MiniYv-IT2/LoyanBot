"""装饰器 — 插件事件绑定"""

from loyan.core.decorators import (
    on_command, on_regex, on_keyword,
    loyan_plugin, plugin_handler,
    require_permission, require_master, require_admin,
    rate_limit, cooldown,
    with_session, async_retry, background,
)
from loyan.core.decorators.registration import on_fallback, DECORATOR_COMMAND_REGISTRY
from loyan.core.decorators.logger import with_logger, log_attrs
from loyan.core.decorators.context import PluginContext


# ── @on_event ──

def on_event(event_type, priority: int = 0):
    """插件订阅业务事件（独立注册，不经命令注册中心）

    用法:
        @on_event("group_member_joined")
        @plugin_handler
        async def on_join(ev: BusinessEvent): ...

    参数:
        event_type: 事件名（如 "group_member_joined"）或 EventType 枚举
        priority:   优先级，越高越先执行（默认 0）
    """
    # 兼容 EventType 枚举传法
    if hasattr(event_type, "value"):
        event_type = event_type.value
    key = f"biz:{event_type}"

    def decorator(func):
        # 函数内延迟 import：核心 bus.py 未就绪时不影响插件加载
        from loyan.core.event import event_bus
        event_bus.subscribe(key, func, priority=priority)
        return func

    return decorator


__all__ = [
    "on_command", "on_regex", "on_keyword",
    "loyan_plugin", "plugin_handler",
    "require_permission", "require_master", "require_admin",
    "rate_limit", "cooldown",
    "with_session", "async_retry", "background",
    "with_logger", "log_attrs",
    "on_fallback", "DECORATOR_COMMAND_REGISTRY",
    "on_event",
    "PluginContext",
]
