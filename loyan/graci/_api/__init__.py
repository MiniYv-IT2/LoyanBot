"""核心 API 组件（发送、配置、服务等）"""
from logging import Logger
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.send import loyan_call_api
from loyan.core.loyan_adapter.send import loyan_get_platform_info

from loyan.core.config import BOT_VERSION
from loyan.core.config import MASTER_ID
from loyan.core.config import ROBOT_ID
from loyan.core.config import ROBOT_START_TIME
from loyan.core.config import LOG_ENCODING
from loyan.core.config import get_current_master_id
from loyan.core.config import get_current_robot_id

from loyan.core.plugin_manager import plugin_manager
from loyan.core.config_manager import config_manager

from loyan.core.utils import logger

def get_logger(name: str):
    return logger.getChild(name)

from loyan.core.security import sanitize_log

from loyan.core.tools.paths import get_logs_dir
from loyan.core.tools.paths import get_storage_dir
from loyan.core.tools.paths import get_res_config_dir
from loyan.core.tools.paths import get_res_dir

from loyan.core.db_manager import get_db

from loyan.core.monitor import monitor_manager

from loyan.core.webserv import Quart, send_from_directory, Blueprint, request, Config, serve

from loyan.core.lifecycle import lifecycle

from loyan.core.pipeline import Stage
from loyan.core.runtime import RuntimeRegistry
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag

__all__ = [
    "loyan_send_msg", "loyan_call_api", "loyan_get_platform_info",
    "BOT_VERSION", "MASTER_ID", "ROBOT_ID", "ROBOT_START_TIME", "LOG_ENCODING",
    "get_current_master_id", "get_current_robot_id",
    "plugin_manager", "config_manager",
    "logger", "get_logger",
    "sanitize_log", "monitor_manager",
    "get_logs_dir", "get_storage_dir", "get_res_config_dir",
    "get_res_dir",
    "get_db",
    "Quart", "send_from_directory", "Blueprint", "request", "Config", "serve",
    "Stage", "RuntimeRegistry", "LoyanEvent", "IdentityTag",
]
