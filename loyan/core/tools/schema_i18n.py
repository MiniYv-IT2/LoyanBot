"""适配器 Schema 国际化工具

将 schema_conf.json 的中文 description 自动转为 i18n key + 翻译字典。
API 返回时使用，不修改源文件。
"""

import json
import os

_SCHEMAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "loyan_adapter", "schemas",
)


def build_adapter_schema_response(adapter_type: str) -> dict | None:
    """读取适配器 schema，返回 metadata + i18n 字典"""
    path = os.path.join(_SCHEMAS_DIR, f"{adapter_type}.schema_conf.json")
    if not os.path.isfile(path):
        return None

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    prefix = f"adapter.{adapter_type}"
    metadata = {}
    i18n = {"zh-CN": {}, "en-US": {}}

    for field_name, field_conf in raw.items():
        entry = {}
        field_i18n_raw = field_conf.pop("i18n", {})
        if not isinstance(field_i18n_raw, dict):
            field_i18n_raw = {}
        for key, value in field_conf.items():
            if key in ("description", "hint", "name"):
                i18n_key = f"{prefix}.{field_name}.{key}"
                entry[key] = i18n_key
                i18n["zh-CN"][i18n_key] = value
            else:
                entry[key] = value
        for lang, translated in field_i18n_raw.items():
            if lang not in i18n:
                i18n[lang] = {}
            if isinstance(translated, str):
                i18n_key = f"{prefix}.{field_name}.description"
                i18n[lang][i18n_key] = translated
            elif isinstance(translated, dict):
                for t_key, t_value in translated.items():
                    i18n_key = f"{prefix}.{field_name}.{t_key}"
                    i18n[lang][i18n_key] = t_value
        metadata[field_name] = entry

    return {"metadata": metadata, "i18n": i18n}


def list_adapter_types() -> list[str]:
    """列出所有可用的适配器类型"""
    if not os.path.isdir(_SCHEMAS_DIR):
        return []
    types = []
    for fname in sorted(os.listdir(_SCHEMAS_DIR)):
        if fname.endswith(".schema_conf.json"):
            types.append(fname.replace(".schema_conf.json", ""))
    return types
