"""用户配置 — 全局默认 + 实例覆盖

全局：storage/config/user_config.json（共享默认）
实例：storage/instances/{name}/user_config.json（独立，覆盖全局）
读取：实例未配字段继承全局（deep_merge）
"""

import json
import os

from loyan.core.config_manager import deep_merge_config


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


def get_global() -> dict:
    return _load_file(_resolve_storage())


def save_global(data: dict) -> None:
    _save_file(_resolve_storage(), data)


def get_instance(instance_name: str) -> dict:
    return _load_file(_instance_file(instance_name))


def save_instance(instance_name: str, data: dict) -> None:
    _save_file(_instance_file(instance_name), data)


def get_effective(instance_name: str) -> dict:
    """实例未配字段继承全局"""
    return deep_merge_config(get_global(), get_instance(instance_name))
