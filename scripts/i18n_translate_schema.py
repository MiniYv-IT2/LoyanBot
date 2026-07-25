"""自动翻译 schema 中缺失的 i18n 字段"""
import json, os, re
import translators as ts

SCHEMA_DIRS = [
    "loyan/core/loyan_adapter/schemas",
    "loyan/brain/provider/schemas",
]
TARGET_LANGS = [
    {"code": "en-US", "from": "zh", "to": "en"},
    {"code": "ru-RU", "from": "zh", "to": "ru"},
]
_HAS_ZH = re.compile(r"[\u4e00-\u9fff]")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for schema_dir in SCHEMA_DIRS:
    for fname in sorted(os.listdir(os.path.join(root, schema_dir))):
        if not fname.endswith(".schema_conf.json"):
            continue
        fpath = os.path.join(root, schema_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        modified = False
        for field, conf in data.items():
            desc = conf.get("description", "")
            if not desc:
                continue
            i18n = conf.setdefault("i18n", {})
            for lang in TARGET_LANGS:
                if lang["code"] in i18n:
                    continue
                if not _HAS_ZH.search(desc):
                    i18n[lang["code"]] = desc
                else:
                    try:
                        r = ts.translate_text(desc, translator="youdao", from_language=lang["from"], to_language=lang["to"])
                        i18n[lang["code"]] = r.strip()
                        print(f"  [{lang['code']}] {desc} → {r.strip()}")
                    except Exception as e:
                        print(f"  !! {desc}: {e}")
                        i18n[lang["code"]] = desc
                modified = True
        if modified:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"✅ {fname}")
