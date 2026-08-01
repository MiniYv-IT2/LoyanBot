"""LoyanBot 顶级包

用法:
    from loyan.graci import on_command, PluginContext
"""

__version__ = "0.1.dev0"

from loyan.core import (
    get_plugin_manager, get_config_manager,
    get_logger_manager, get_runtime_registry,
    logger, __version__,
)

__all__ = [
    "get_plugin_manager", "get_config_manager",
    "get_logger_manager", "get_runtime_registry",
    "logger", "__version__",
]
