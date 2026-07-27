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

__all__ = [
    "on_command", "on_regex", "on_keyword",
    "loyan_plugin", "plugin_handler",
    "require_permission", "require_master", "require_admin",
    "rate_limit", "cooldown",
    "with_session", "async_retry", "background",
    "with_logger", "log_attrs",
    "on_fallback", "DECORATOR_COMMAND_REGISTRY",
    "PluginContext",
]
