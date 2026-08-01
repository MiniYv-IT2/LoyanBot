"""LoyanBot 框架级配置包

模块 → 包重构：原 config.py 拆为 default.py + schema/i18n 文件，
本文件重导出全部符号，现有 `from loyan.core.config import XXX` 零改动。
"""

from .base import (
    DEFAULT_CONFIG,
    config_manager,
    BOT_VERSION,
    LOG_ENCODING,
    AUTO_REPLIES,
    DEBUG_MODE,
    LOG_LEVEL,
    ROBOT_ID,
    MASTER_ID,
    ROBOT_START_TIME,
    get_current_robot_id,
    get_current_master_id,
)
from loyan.core.config_manager import ConfigItem

__all__ = [
    "DEFAULT_CONFIG",
    "config_manager",
    "ConfigItem",
    "BOT_VERSION",
    "LOG_ENCODING",
    "AUTO_REPLIES",
    "DEBUG_MODE",
    "LOG_LEVEL",
    "ROBOT_ID",
    "MASTER_ID",
    "ROBOT_START_TIME",
    "get_current_robot_id",
    "get_current_master_id",
]
