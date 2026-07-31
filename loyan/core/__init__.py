"""LoyanBot 核心模块统一导入文件

此模块提供核心组件的统一导出，简化其他模块的导入路径，提高代码可维护性。
"""


def get_plugin_manager():
    """获取插件管理器实例（延迟导入，避免循环依赖）"""
    from .plugin_manager import plugin_manager
    return plugin_manager


def get_config_manager():
    """获取配置管理器实例（延迟导入，避免循环依赖）"""
    from .config_manager import config_manager
    return config_manager


def get_logger_manager():
    """获取日志管理器实例（延迟导入，避免循环依赖）"""
    from .logger_manager import logger_manager
    return logger_manager


def get_runtime_registry():
    """获取 Runtime 注册表实例（延迟导入，避免循环依赖）"""
    from .runtime import RuntimeRegistry
    return RuntimeRegistry


# 导出主要工具函数和常量（容错导入，避免缺依赖时崩整个包）
try:
    from loyan.core.utils import logger
except ImportError:
    logger = None

# 版本信息（懒加载，避免导入时触发配置系统）
def _get_version():
    from loyan.core.config import BOT_VERSION
    return BOT_VERSION

__version__ = _get_version()
__all__ = [
    "get_plugin_manager",
    "get_config_manager",
    "get_logger_manager",
    "get_runtime_registry",
    "logger",
    "__version__"
]
