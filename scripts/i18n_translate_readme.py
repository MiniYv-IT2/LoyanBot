"""翻译 README.md 到各语言

不翻译的内容:
- 包含 HTML 标签的行（保留原样）
- URL / 图片 / badge
- 代码块 / 行内代码
- 版本号 / 专有名词（翻译后回查替换）
"""

import os, re, translators as ts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "README.md")
TARGETS = [
    {"suffix": "_zh-CN", "from": "en", "to": "zh-CHS"},
    {"suffix": "_zh-TW", "from": "en", "to": "zh-CHT"},
    {"suffix": "_RU", "from": "en", "to": "ru"},
    {"suffix": "_FR", "from": "en", "to": "fr"},
    {"suffix": "_KO", "from": "en", "to": "ko"},
]

HAS_HTML = re.compile(r"<[^>]+>")
HAS_URL = re.compile(r"https?://\S+")
HAS_CODE = re.compile(r"`[^`]+`")
IS_TABLE = re.compile(r"^\|.*\|.*\|$")  # Markdown 表格行

# 专有名词保护（翻译后回查替换，忽略大小写差异）
PROTECTED = {
    "洛颜 LoyanBot": ["洛颜 LoyanBot", "洛颜LoyanBot", "洛颜", "LuoyanBot", "Loyan机器人", "Loyan-бот", "Loyan бот"],
    "LoyanBot": ["LoyanBot", "洛岩Bot", "洛岩机器人", "Loyan机器人", "Loyan-бот", "Loyan бот"],
    "GracyBot": ["GracyBot"],
    "Pipeline": ["Pipeline", "管道调度", "管道", "трубопровод"],
    "Agent": ["Agent", "代理系统", "代理", "агент"],
    "LLM": ["LLM", "LLM"],
    "Python": ["Python"],
    "Quart": ["Quart"],
    "Docker": ["Docker"],
    "GPL-3.0": ["GPL-3.0", "GPL 3.0", "GPL-3"],
    "MIT": ["MIT"],
    "MiniYv-IT2": ["MiniYv-IT2", "MiniYv‑IT2", "MiniYv-IT2组织"],
    "MiniYv": ["MiniYv", "MiniYv", "МиниЙв", "MinYv"],
}

# 机器翻译常见误译修正（只改明显错误的词）
TRANSLATION_FIXES = {
    "zh-CN": {"内存与上下文管理": "记忆与上下文管理", "b微信": "微信", "MiniYv- it2": "MiniYv-IT2", "MiniYv‑it2": "MiniYv-IT2"},
    "zh-TW": {"內存與上下文管理": "記憶與上下文管理", "b微信": "微信"},
    "RU": {},
    "FR": {},
    "KO": {},
}

def has_skip_content(line: str) -> bool:
    return bool(HAS_HTML.search(line) or HAS_URL.search(line) or HAS_CODE.search(line) or IS_TABLE.match(line))

def restore_protected(text: str) -> str:
    for original, variants in PROTECTED.items():
        for v in variants:
            if v.lower() in text.lower():
                text = re.sub(re.escape(v), original, text, flags=re.IGNORECASE)
                break
    return text

with open(SRC, encoding="utf-8") as f:
    lines = f.readlines()

for target in TARGETS:
    out_path = os.path.join(ROOT, f"README{target['suffix']}.md")
    out_lines = []
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped.strip() or has_skip_content(stripped):
            out_lines.append(stripped)
        else:
            try:
                translated = ts.translate_text(stripped, translator="youdao", from_language=target["from"], to_language=target["to"])
                translated = restore_protected(translated.strip())
                # 应用误译修正
                fixes = TRANSLATION_FIXES.get(target["suffix"].lstrip("_"), {})
                for wrong, correct in fixes.items():
                    translated = translated.replace(wrong, correct)
                out_lines.append(translated)
            except Exception:
                out_lines.append(stripped)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print(f"✅ README{target['suffix']}.md")
