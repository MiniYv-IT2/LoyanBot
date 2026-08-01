"""LoyanBot 框架级配置 — config.json 中的全局配置项

robot_id / master_id 等实例级配置已迁移到 storage/instances/<name>/config.json，
每个实例独立管理，不再全局共享。

配置唯一来源：settings.schema_conf.json（字段定义 + 默认值）。
本文件只做：生成 DEFAULT_CONFIG、暴露常量。
"""

import os
import time
from loyan import __version__ as BOT_VERSION
from loyan.core.config_manager import config_manager

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "settings.schema_conf.json")


# ═══════════════ 框架默认值（schema 为唯一来源，注册在 config_manager 内完成） ═══════════════

DEFAULT_CONFIG = config_manager.schema_defaults(
    config_manager.register_configs_from_schema(_SCHEMA_PATH)
)
"""完整默认配置字典（框架级，不含实例级字段如 robot_id/master_id）。"""

# ═══════════════ 加载配置 ═══════════════

if not config_manager.load():
    pass

config_manager._auto_update_config(DEFAULT_CONFIG)
config_manager.load()

# ═══════════════ 模块常量（框架级，不包含实例级字段） ═══════════════

LOG_ENCODING = config_manager.get("log_encoding")
AUTO_REPLIES = config_manager.get("auto_replies")
DEBUG_MODE = config_manager.get("debug_mode")
LOG_LEVEL = config_manager.get("log_level")

# robot_id / master_id 已迁移到各实例配置文件 + RuntimeRegistry
# 旧代码通过 get_current_robot_id() / get_current_master_id() 从 RuntimeContext 获取
ROBOT_ID = ""
MASTER_ID = ""
ROBOT_START_TIME = time.time()


def get_current_robot_id() -> str:
    """获取当前消息上下文中的机器人 ID（多实例时自动适配当前账号）

    插件在消息处理中调用此函数代替直接使用 ROBOT_ID，
    多账号场景下会自动返回正确的机器人 ID。
    无上下文时回退到第一个 Runtime 的 robot_id。
    """
    try:
        from loyan.core.runtime import RuntimeContext
        runtime = RuntimeContext.get()
        if runtime and runtime.robot_id:
            return runtime.robot_id
    except Exception:
        pass
    # 无上下文时尝试第一个 Runtime（如插件 on_ready 线程）
    try:
        from loyan.core.runtime import RuntimeRegistry
        runtimes = RuntimeRegistry.get_all()
        if runtimes and runtimes[0].robot_id:
            return runtimes[0].robot_id
    except Exception:
        pass
    return ROBOT_ID


def get_current_master_id() -> str:
    """获取当前消息上下文中的主人 ID（多实例时自动适配当前账号）

    插件在消息处理中调用此函数代替直接使用 MASTER_ID，
    多账号场景下会自动返回当前消息来源实例配置的主人 ID。
    无上下文时回退到第一个 Runtime 的 master_id。
    """
    try:
        from loyan.core.runtime import RuntimeContext
        runtime = RuntimeContext.get()
        if runtime and runtime.master_id:
            return runtime.master_id
    except Exception:
        pass
    # 无上下文时尝试第一个 Runtime（如插件 on_ready 线程）
    try:
        from loyan.core.runtime import RuntimeRegistry
        runtimes = RuntimeRegistry.get_all()
        if runtimes and runtimes[0].master_id:
            return runtimes[0].master_id
    except Exception:
        pass
    return MASTER_ID
