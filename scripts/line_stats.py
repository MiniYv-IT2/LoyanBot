"""统计源码行数，生成 HTML 卡片嵌入 README"""

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
BAR_BG = "#8ecac822"

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
    bar_w = max(1, int(pct))
    bar_color = COLORS.get(name, "#888")
    ROWS.append(
        f'<div style="display:flex;align-items:center;margin:3px 0;font-size:13px;">'
        f'<span style="width:85px;text-align:right;padding-right:8px;color:#555;">{name}</span>'
        f'<div style="flex:1;height:14px;max-width:200px;">'
        f'<div style="display:flex;height:14px;width:100%;background:{BAR_BG};">'
        f'<div style="width:{pct:.1f}%;height:14px;background:{bar_color};"></div>'
        f'</div>'
        f'</div>'
        f'<span style="width:50px;text-align:right;padding-left:6px;color:#888;font-size:12px;">{pct:.1f}%</span>'
        f'<span style="width:60px;text-align:right;padding-left:4px;color:#999;font-size:12px;">{counts[ext]:,}</span>'
        f'</div>'
    )

card = (
    f'<div style="border:1px solid #e0e0e0;border-radius:10px;padding:18px 20px;'
    f'max-width:460px;margin:14px auto;background:#fef5e7;">\n'
    f'<div style="font-size:15px;font-weight:600;color:#222;margin-bottom:10px;">'
    f'Source Code Stats</div>\n'
    + "\n".join(ROWS) +
    f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #eee;'
    f'font-size:13px;color:#999;">'
    f'<span style="color:#333;font-weight:600;">{total:,}</span> total · '
    f'<span style="color:#333;font-weight:600;">{len(EXTENSIONS)}</span> languages'
    f'</div>\n</div>'
)

with open(README, encoding="utf-8") as f:
    content = f.read()

marker_start = "<!-- STATS_CARD_START -->"
marker_end = "<!-- STATS_CARD_END -->"
new_section = f"{marker_start}\n{card}\n{marker_end}"

if marker_start in content:
    content = re.sub(f"{marker_start}.*?{marker_end}", new_section, content, flags=re.DOTALL)
else:
    content = content.replace("A multi-platform", f"{new_section}\n\nA multi-platform")

with open(README, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ README updated: {total:,} lines")
