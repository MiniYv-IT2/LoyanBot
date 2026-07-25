"""生成多语言源码统计 SVG 卡片"""
import subprocess, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_DIR = os.path.join(ROOT, "svg")
os.makedirs(SVG_DIR, exist_ok=True)
BG = "#87CEEB"  # 天蓝色

EXTENSIONS = [
    ("py", "Python"),
    ("jsx", "React JSX"),
    ("ts", "TypeScript"),
    ("js", "JavaScript"),
    ("json", "JSON"),
]
COLORS = ["#5ba3cf", "#4a92be", "#3a82ae", "#2a729e", "#1a628e"]

LANGS = {
    "": {"title": "Source Code Stats", "total": "total", "langs": "languages"},
    "_zh-CN": {"title": "源码统计", "total": "行", "langs": "种语言"},
    "_zh-TW": {"title": "源碼統計", "total": "行", "langs": "種語言"},
    "_RU": {"title": "Статистика кода", "total": "строк", "langs": "языков"},
    "_FR": {"title": "Stats du code", "total": "lignes", "langs": "langues"},
    "_KO": {"title": "코드 통계", "total": "줄", "langs": "언어"},
}

total = 0
counts = {}
for ext, name in EXTENSIONS:
    r = subprocess.run(
        ["find", "loyan", "panel/src", "panel/tests", "scripts",
         "-name", f"*.{ext}", "-not", "-path", "*/panel-dist/*",
         "-exec", "wc", "-l", "{}", "+"],
        capture_output=True, text=True, cwd=ROOT,
    )
    lines = r.stdout.strip().split("\n")
    count = int(lines[-1].split()[0]) if lines[-1] else 0
    counts[ext] = count
    total += count

PAD = 20; LABEL_W = 85; BAR_W = 200; PCT_W = 50; NUM_W = 70
ROW_H = 30; HEADER_H = 40; FOOTER_H = 35
W = PAD * 2 + LABEL_W + BAR_W + PCT_W + NUM_W
H = PAD * 2 + HEADER_H + len(EXTENSIONS) * ROW_H + FOOTER_H

for suffix, txt in LANGS.items():
    fname = f"stats-card{suffix}.svg"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
    svg += f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="#bbb" stroke-width="1"/>'
    svg += f'<text x="{W/2}" y="{PAD + 22}" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="bold" fill="#fff">{txt["title"]}</text>'
    svg += f'<line x1="{PAD}" y1="{PAD + HEADER_H}" x2="{W - PAD}" y2="{PAD + HEADER_H}" stroke="rgba(255,255,255,0.3)" stroke-width="1"/>'

    for i, (ext, name) in enumerate(EXTENSIONS):
        pct = counts[ext] / total * 100 if total else 0
        bw = int(BAR_W * pct / 100)
        row_y = PAD + HEADER_H + 4 + i * ROW_H
        svg += f'<text x="{PAD}" y="{row_y + 16}" text-anchor="start" font-family="sans-serif" font-size="13" fill="#fff">{name}</text>'
        svg += f'<rect x="{PAD + LABEL_W}" y="{row_y + 4}" width="{BAR_W}" height="18" rx="4" fill="rgba(255,255,255,0.3)"/>'
        if bw > 0:
            svg += f'<rect x="{PAD + LABEL_W}" y="{row_y + 4}" width="{bw}" height="18" rx="4" fill="{COLORS[i]}"/>'
        svg += f'<text x="{PAD + LABEL_W + BAR_W + 6}" y="{row_y + 16}" text-anchor="start" font-family="sans-serif" font-size="12" fill="#fff">{pct:.1f}%</text>'
        svg += f'<text x="{PAD + LABEL_W + BAR_W + PCT_W + 6}" y="{row_y + 16}" text-anchor="start" font-family="sans-serif" font-size="12" fill="#fff">{counts[ext]:,}</text>'

    footer_y = PAD + HEADER_H + len(EXTENSIONS) * ROW_H
    svg += f'<line x1="{PAD}" y1="{footer_y}" x2="{W - PAD}" y2="{footer_y}" stroke="rgba(255,255,255,0.3)" stroke-width="1"/>'
    svg += f'<text x="{W/2}" y="{footer_y + 22}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">'
    svg += f'<tspan font-weight="bold">{total:,}</tspan> {txt["total"]} · '
    svg += f'<tspan font-weight="bold">{len(EXTENSIONS)}</tspan> {txt["langs"]}'
    svg += f'</text></svg>'

    path = os.path.join(SVG_DIR, fname)
    with open(path, "w") as f:
        f.write(svg)
    print(f"✅ svg/{fname}")

# 更新各 README 的 STATS_CARD 区域为对应语言的 SVG
IMG_MAP = {f"README{suffix}.md": f"svg/stats-card{suffix}.svg" for suffix in LANGS}
IMG_MAP["README.md"] = "svg/stats-card.svg"

for fpath in glob.glob(os.path.join(ROOT, "README*.md")):
    fname = os.path.basename(fpath)
    img = IMG_MAP.get(fname, "stats-card.svg")
    tag = f'<div align="center"><img src="{img}" alt="Source Code Stats"></div>'
    ms = "<!-- STATS_CARD_START -->"
    me = "<!-- STATS_CARD_END -->"
    new_section = f"{ms}\n{tag}\n{me}"
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    if ms in content:
        content = re.sub(f"{ms}.*?{me}", new_section, content, flags=re.DOTALL)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

print(f"✅ 已更新 {len(glob.glob(os.path.join(ROOT, 'README*.md')))} 个 README")
