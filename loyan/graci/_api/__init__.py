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
from loyan.core.tools.paths import get_plugin_data_dir

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
    "get_res_dir", "get_plugin_data_dir",
    "get_db",
    "Quart", "send_from_directory", "Blueprint", "request", "Config", "serve",
    "Stage", "RuntimeRegistry", "LoyanEvent", "IdentityTag",
    "check_update", "apply_update", "get_update_log",
]


# ── 本体更新透传 ──

async def check_update():
    """检查本体更新，返回 {available, current, latest, changelog}"""
    from loyan.core.update_manager import update_manager
    try:
        return await update_manager.check()
    finally:
        await update_manager.close()


async def apply_update():
    """应用本体更新（下载+校验+覆盖）"""
    from loyan.core.update_manager import update_manager
    try:
        return await update_manager.apply()
    finally:
        await update_manager.close()


def get_update_log() -> list:
    """读取本地 updates/ 更新日志文件名列表（最近在前）"""
    import os
    from loyan.core.tools.paths import get_project_root
    updates_dir = os.path.join(get_project_root(), "updates")
    if not os.path.isdir(updates_dir):
        return []
    files = sorted((f for f in os.listdir(updates_dir) if f.endswith(".md")), reverse=True)
    return files[:10]
