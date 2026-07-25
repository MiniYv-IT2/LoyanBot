"""统计源码行数，生成简单表格嵌入 README"""

import subprocess, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

EXTENSIONS = [
    ("py", "Python"),
    ("jsx", "React JSX"),
    ("ts", "TypeScript"),
    ("js", "JavaScript"),
    ("json", "JSON"),
]
COLORS = {
    "Python": "#8ecac8",
    "React JSX": "#7abfbc",
    "TypeScript": "#66b4b0",
    "JavaScript": "#52a9a4",
    "JSON": "#3e9e98",
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

ROWS = []
for ext, name in EXTENSIONS:
    pct = counts[ext] / total * 100 if total else 0
    bar_color = COLORS.get(name, "#888")
    ROWS.append(
        f'<tr><td>{name}</td><td align="right">{counts[ext]:,}</td>'
        f'<td align="right">{pct:.1f}%</td></tr>'
    )

table = (
    f'| Language | Lines | % |\n'
    f'|:--------:|:----:|:---:|\n'
)
for ext, name in EXTENSIONS:
    pct = counts[ext] / total * 100 if total else 0
    table += f'| {name} | {counts[ext]:,} | {pct:.1f}% |\n'
table += f'| **Total** | **{total:,}** | **100%** |\n'

with open(README, encoding="utf-8") as f:
    content = f.read()

marker_start = "<!-- STATS_CARD_START -->"
marker_end = "<!-- STATS_CARD_END -->"
new_section = f"{marker_start}\n<div align=\"center\">\n\n{table}\n</div>\n{marker_end}"

if marker_start in content:
    content = re.sub(f"{marker_start}.*?{marker_end}", new_section, content, flags=re.DOTALL)
else:
    content = content.replace("A multi-platform", f"{new_section}\n\nA multi-platform")

with open(README, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ README updated: {total:,} lines")
