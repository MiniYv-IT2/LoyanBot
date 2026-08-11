"""装饰器 — 插件事件绑定"""

from loyan.core.decorators import (
    on_command, on_regex, on_keyword,
    loyan_plugin, plugin_handler,
    require_permission, require_master, require_admin,
    rate_limit, cooldown,
    with_session, async_retry, background,
)
from loyan.core.decorators.registration import (
    on_fallback, DECORATOR_COMMAND_REGISTRY,
    brain_tool, list_brain_tools, call_brain_tool,
)
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
    "brain_tool", "list_brain_tools", "call_brain_tool",
    "PluginContext",
    "disable_plugin",
]


# ── 插件管理透传（薄转发，无业务逻辑） ──

async def _await_maybe(result):
    import inspect
    if inspect.iscoroutine(result):
        return await result
    return result


async def disable_plugin(name: str):
    from loyan.core.plugin_manager import plugin_manager
    return await _await_maybe(plugin_manager.disable_plugin(name))
