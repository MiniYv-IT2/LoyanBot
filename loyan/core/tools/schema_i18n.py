"""适配器/提供商 Schema 国际化工具"""

import asyncio
import json
import os

_SOURCE_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "loyan_adapter", "source"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 "brain", "provider", "source"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "config"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "webserv", "panel", "source"),
]


async def _load_file(path: str) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: open(path, encoding="utf-8").read())
    except FileNotFoundError:
        return None


async def _load_schema(schema_type: str) -> tuple[dict | None, dict | None]:
    for base in _SOURCE_DIRS:
        conf_path = os.path.join(base, f"{schema_type}.schema_conf.json")
        conf_raw = await _load_file(conf_path)
        if conf_raw is None:
            continue
        raw = json.loads(conf_raw)
        i18n_path = os.path.join(base, "i18n", f"{schema_type}.json")
        i18n_raw = await _load_file(i18n_path)
        i18n_data = json.loads(i18n_raw) if i18n_raw else {}
        return raw, i18n_data
    return None, None


async def build_schema_response(schema_type: str) -> dict | None:
    raw, i18n_data = await _load_schema(schema_type)
    if raw is None:
        return None

    prefix = f"{schema_type}"
    metadata = {}
    i18n = {"zh-CN": {}, "en-US": {}, "ru-RU": {}}

    for field_name, field_conf in raw.items():
        entry = {}
        field_i18n = i18n_data.get(field_name, {})
        for key, value in field_conf.items():
            if key in ("description", "hint", "name"):
                i18n_key = f"{prefix}.{field_name}.{key}"
                entry[key] = i18n_key
                i18n["zh-CN"][i18n_key] = value
            else:
                entry[key] = value
        for lang, translations in field_i18n.items():
            if lang not in i18n:
                i18n[lang] = {}
            if isinstance(translations, str):
                i18n_key = f"{prefix}.{field_name}.description"
                i18n[lang][i18n_key] = translations
            elif isinstance(translations, dict):
                for t_key, t_value in translations.items():
                    i18n_key = f"{prefix}.{field_name}.{t_key}"
                    i18n[lang][i18n_key] = t_value
        metadata[field_name] = entry

    return {"metadata": metadata, "i18n": i18n}


async def list_source_types() -> list[str]:
    loop = asyncio.get_running_loop()
    types = []
    for base in _SOURCE_DIRS:
        if not os.path.isdir(base):
            continue
        def _scan(base=base):
            result = []
            for fname in sorted(os.listdir(base)):
                if fname.endswith(".schema_conf.json"):
                    result.append(fname.replace(".schema_conf.json", ""))
            return result
        found = await loop.run_in_executor(None, _scan)
        for t in found:
            if t not in types:
                types.append(t)
    return types

async def list_adapter_types() -> list[str]:
    """仅返回消息平台适配器类型（不包含 provider）。"""
    loop = asyncio.get_running_loop()
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "loyan_adapter", "source")
    if not os.path.isdir(base):
        return []
    def _scan():
        result = []
        for fname in sorted(os.listdir(base)):
            if fname.endswith(".schema_conf.json"):
                result.append(fname.replace(".schema_conf.json", ""))
        return result
    return await loop.run_in_executor(None, _scan)
