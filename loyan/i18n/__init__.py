"""国际化 — 仅 brain 模块使用，不依赖 core"""

import json
import os
from functools import lru_cache
from typing import Optional

_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_LANG = "zh-CN"


@lru_cache(maxsize=2)
def _load(lang: str) -> dict:
    path = os.path.join(_DIR, f"{lang}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get(d: dict, key: str) -> Optional[str]:
    parts = key.split(".")
    for p in parts:
        if not isinstance(d, dict):
            return None
        d = d.get(p, {})
    return d if isinstance(d, str) else None


def t(key: str, lang: str = _DEFAULT_LANG, **kwargs) -> str:
    """翻译：t("provider.auth_failed") 或 t("chat.no_reply")"""
    msg = _get(_load(lang), key) or _get(_load(_DEFAULT_LANG), key) or key
    if kwargs:
        msg = msg.format(**kwargs)
    return msg
