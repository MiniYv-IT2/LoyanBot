"""用户配置 — 全局默认 + 实例覆盖

全局：storage/config/user_config.json（共享默认）
实例：storage/instances/{name}/user_config.json（独立，覆盖全局）
读取：实例未配字段继承全局（deep_merge）
"""

import json
import os
import time

from loyan.core.config_manager import deep_merge_config

_CACHE_TTL = 30.0
_cache: dict = {}
_cache_ts: float = 0.0


def _resolve_storage() -> str:
    from loyan.core.tools.paths import get_storage_dir
    return os.path.join(get_storage_dir(), "config", "user_config.json")


def _load_file(filepath: str) -> dict:
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_file(filepath: str, data: dict) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _instance_file(instance_name: str) -> str:
    from loyan.core.tools.paths import get_instances_dir
    return os.path.join(get_instances_dir(), instance_name, "user_config.json")


def _schema_defaults() -> dict:
    """从 user_config.schema_conf.json 生成默认配置（复用 config_manager 的 schema_defaults）"""
    from loyan.core.config_manager import config_manager
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "user_config.schema_conf.json")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception:
        return {}
    return config_manager.schema_defaults(schema)


def get_global() -> dict:
    data = _load_file(_resolve_storage())
    if data:
        return data
    defaults = _schema_defaults()
    _save_file(_resolve_storage(), defaults)
    return defaults


def save_global(data: dict) -> None:
    _save_file(_resolve_storage(), data)


def get_instance(instance_name: str) -> dict:
    return _load_file(_instance_file(instance_name))


def save_instance(instance_name: str, data: dict) -> None:
    _save_file(_instance_file(instance_name), data)


def get_effective(instance_name: str) -> dict:
    """实例未配字段继承全局"""
    return deep_merge_config(get_global(), get_instance(instance_name))


def get_effective_cached(instance_name: str) -> dict:
    """带 TTL 缓存的 effective（每消息匹配调用，避免频繁读文件）"""
    global _cache, _cache_ts
    key = instance_name or "_"
    now = time.monotonic()
    if now - _cache_ts > _CACHE_TTL or key not in _cache:
        _cache[key] = get_effective(instance_name)
        _cache_ts = now
    return _cache[key]
