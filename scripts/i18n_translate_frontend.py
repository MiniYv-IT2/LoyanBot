"""翻译前端 i18n .ts 文件中缺失的语言"""
import os, re, translators as ts

LOCALES = os.path.join(os.path.dirname(__file__), "..", "panel", "src", "i18n", "locales")
SOURCE = "zh-CN"
TARGETS = ["en-US", "ru-RU"]

EXTRACT_KEY = re.compile(r'^\s+["\']?(\w+)["\']?\s*:\s*["\'](.+?)["\']')

for dirpath, _dirnames, files in os.walk(os.path.join(LOCALES, SOURCE)):
    for fname in files:
        if not fname.endswith(".ts") or fname == "index.ts":
            continue
        src_path = os.path.join(dirpath, fname)
        with open(src_path, encoding="utf-8") as f:
            lines = f.readlines()

        keys = {}
        for line in lines:
            m = EXTRACT_KEY.search(line)
            if m:
                keys[m.group(1)] = m.group(2)

        for target in TARGETS:
            tgt_dir = dirpath.replace(SOURCE, target)
            os.makedirs(tgt_dir, exist_ok=True)
            tgt_path = os.path.join(tgt_dir, fname)
            if os.path.isfile(tgt_path):
                continue  # 已有翻译文件就跳过

            new_lines = []
            for line in lines:
                m = EXTRACT_KEY.search(line)
                if m and m.group(1) in keys:
                    val = keys[m.group(1)]
                    try:
                        r = ts.translate_text(val, translator="youdao", from_language="zh", to_language="en" if target == "en-US" else "ru")
                        new_lines.append(line.replace(f'"{val}"', f'"{r.strip()}"').replace(f"'{val}'", f"'{r.strip()}'"))
                    except Exception as e:
                        print(f"  !! {m.group(1)}: {e}")
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            with open(tgt_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"✅ {target}/{fname}")
