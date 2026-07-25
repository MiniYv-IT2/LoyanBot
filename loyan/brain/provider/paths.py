"""Brain 路径管理"""

import os


def _brain_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_schemas_dir() -> str:
    return os.path.join(_brain_root(), "provider", "schemas")


def get_types_dir() -> str:
    return os.path.join(_brain_root(), "provider", "types")
