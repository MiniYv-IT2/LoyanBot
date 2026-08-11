"""LoyanBot 统一路径解析

所有路径从 get_project_root() 派生，不散落各处读环境变量。

优先级:
  1. GRACYBOT_HOME 环境变量（Docker / systemd）
  2. CWD 有 bot.py（本地项目开发）
  3. site-packages 安装目录
  4. CWD

用法:
    from loyan.core.tools.paths import get_plugins_dir, get_config_path
"""

import os
import functools
from contextvars import ContextVar

_ROOT_ENV_VAR = "GRACYBOT_HOME"

# 插件加载时由 plugin_manager 设置，LoyanPaths 自动绑定当前插件名
_current_plugin: ContextVar[str] = ContextVar("loyan_current_plugin", default="")


@functools.lru_cache(maxsize=1)
def get_project_root() -> str:
    if root := os.environ.get(_ROOT_ENV_VAR):
        return os.path.realpath(root)

    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "bot.py")):
        return os.path.realpath(cwd)

    return os.path.realpath(cwd)


@functools.lru_cache(maxsize=1)
def get_storage_dir() -> str:
    return os.path.join(get_project_root(), "storage")


@functools.lru_cache(maxsize=1)
def get_plugins_dir() -> str:
    return os.path.join(get_project_root(), "loyan", "plugins")


@functools.lru_cache(maxsize=1)
def get_user_plugins_dir() -> str:
    return os.path.join(get_storage_dir(), "plugins")


@functools.lru_cache(maxsize=1)
def get_instances_dir() -> str:
    return os.path.join(get_storage_dir(), "instances")


@functools.lru_cache(maxsize=1)
def get_config_path() -> str:
    return os.path.join(get_storage_dir(), "config.json")


@functools.lru_cache(maxsize=1)
def get_disabled_plugins_path() -> str:
    return os.path.join(get_storage_dir(), ".loyan_disabled.json")


@functools.lru_cache(maxsize=1)
def get_res_config_dir() -> str:
    return os.path.join(get_storage_dir(), "config")


@functools.lru_cache(maxsize=1)
def get_logs_dir() -> str:
    return os.path.join(get_storage_dir(), "logs")


@functools.lru_cache(maxsize=1)
def get_data_dir() -> str:
    return os.path.join(get_storage_dir(), "data")


def get_plugin_data_dir(plugin_name: str) -> str:
    """插件运行时数据目录：storage/data/plugins/{插件名}/

    运行时数据（图片/缓存/日志）统一放这里，不落插件代码目录，
    避免插件目录变化触发 watchfiles 热重载。
    """
    return os.path.join(get_data_dir(), "plugins", plugin_name)


def get_db_path(plugin_name: str) -> str:
    return os.path.join(get_data_dir(), f"{plugin_name}.db")


@functools.lru_cache(maxsize=1)
def get_plugin_config_global_dir() -> str:
    return os.path.join(get_storage_dir(), "config")


def get_plugin_config_instance_dir(instance_name: str) -> str:
    return os.path.join(get_instances_dir(), instance_name, "plugins")


def get_res_dir() -> str:
    return os.path.join(get_project_root(), "loyan", "res", "resource")


def invalidate_cache() -> None:
    get_project_root.cache_clear()
    get_storage_dir.cache_clear()
    get_plugins_dir.cache_clear()
    get_user_plugins_dir.cache_clear()
    get_instances_dir.cache_clear()
    get_config_path.cache_clear()
    get_disabled_plugins_path.cache_clear()
    get_res_config_dir.cache_clear()
    get_logs_dir.cache_clear()
    get_data_dir.cache_clear()
    get_plugin_config_global_dir.cache_clear()


class LoyanPaths:
    """插件统一路径入口：data / res / db / temp 一条龙"""

    def __init__(self, plugin_name: str = "") -> None:
        self._plugin_name = plugin_name or _current_plugin.get()
        if not self._plugin_name:
            raise ValueError("LoyanPaths 需要插件名：显式传入或在插件加载时设置 _current_plugin")

    @staticmethod
    def storage(rel: str = "") -> str:
        """框架存储根目录 storage/{rel}（不依赖插件名）"""
        base = get_storage_dir()
        if rel:
            parts = [p for p in rel.replace("\\", "/").split("/") if p]
            if ".." in parts:
                raise ValueError(f"相对路径禁止 '..' 穿越: {rel}")
            base = os.path.join(base, *parts)
        return base

    @staticmethod
    def framework_res(rel: str = "") -> str:
        """框架全局资源目录 loyan/res/resource/{rel}（不依赖插件名）"""
        base = get_res_dir()
        if rel:
            parts = [p for p in rel.replace("\\", "/").split("/") if p]
            if ".." in parts:
                raise ValueError(f"相对路径禁止 '..' 穿越: {rel}")
            base = os.path.join(base, *parts)
        return base

    def data(self, rel: str = "") -> str:
        """插件数据目录 storage/data/plugins/{插件名}/{rel}"""
        return self._safe_join(os.path.join(get_data_dir(), "plugins", self._plugin_name), rel)

    def res(self, rel: str = "") -> str:
        """插件资源目录 {插件注册目录}/res/{rel}，注册目录从 registry 查"""
        from loyan.core.plugin_manager import plugin_manager

        base = ""
        for entry in plugin_manager.registry:
            if entry.get("name") == self._plugin_name:
                base = entry.get("plugin_path") or ""
                break
        if not base:
            raise ValueError(f"插件 {self._plugin_name} 未在 registry 中注册")
        return self._safe_join(os.path.join(base, "res"), rel)

    def db(self, name: str = None) -> str:
        """插件数据库文件路径，name 只允许字母数字下划线中文连字符"""
        if name is None:
            name = self._plugin_name
        safe = "".join(c if (c.isalnum() or c in "_-") else "_" for c in name)
        return self._safe_join(os.path.join(get_data_dir(), "plugins", self._plugin_name), f"{safe}.db")

    def temp(self, rel: str = "") -> str:
        """插件临时目录 storage/data/plugins/{插件名}/.tmp/{rel}"""
        return self._safe_join(os.path.join(get_data_dir(), "plugins", self._plugin_name, ".tmp"), rel)

    def _safe_join(self, base: str, rel: str) -> str:
        """净化 rel（拒 '..' 段）、自动 makedirs、返回完整路径"""
        if rel:
            parts = [p for p in rel.replace("\\", "/").split("/") if p]
            if ".." in parts:
                raise ValueError(f"相对路径禁止 '..' 穿越: {rel}")
            base = os.path.join(base, *parts)
        os.makedirs(base, exist_ok=True)
        return base
