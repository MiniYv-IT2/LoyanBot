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
    bar_color = COLORS.get(name, "#888")
    ROWS.append(
        f'<tr>'
        f'<td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">{name}</td>'
        f'<td style="padding:2px 0;width:200px;">'
        f'<table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:{BAR_BG};">'
        f'<tr>'
        f'<td style="width:{pct:.1f}%;height:14px;background:{bar_color};padding:0;border:none;"></td>'
        f'<td style="padding:0;border:none;"></td>'
        f'</tr></table>'
        f'</td>'
        f'<td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">{pct:.1f}%</td>'
        f'<td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">{counts[ext]:,}</td>'
        f'</tr>'
    )

card = (
    f'<table style="border:1px solid #ddd;padding:10px 14px;'
    f'max-width:460px;margin:16px auto;background:#fef5e7;">\n'
    f'<tr><td colspan="4" style="text-align:center;font-size:15px;font-weight:600;color:#222;padding-bottom:8px;">'
    f'Source Code Stats</td></tr>\n'
    + "\n".join(ROWS) +
    f'<tr><td colspan="4" style="text-align:center;font-size:13px;color:#888;padding-top:8px;border-top:1px solid #eee;">'
    f'<b style="color:#333;">{total:,}</b> total · '
    f'<b style="color:#333;">{len(EXTENSIONS)}</b> languages'
    f'</td></tr>\n'
    f'</table>'
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
