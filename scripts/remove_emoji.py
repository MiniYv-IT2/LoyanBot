"""删除 Python 文件日志中的表情符号"""
import re, sys

EMOJI = re.compile(
    "[\U0001F300-\U0001F9FF"  # 杂项符号、表情、补充符号
    "\U0001FA00-\U0001FA6F"  # 象棋符号
    "\U0001FA70-\U0001FAFF"  # 几何符号扩展
    "\u2600-\u27BF"          # 杂项符号
    "\u2702-\u27B0"          # 丁字符号
    "\uFE00-\uFE0F"          # 变化选择器
    "\U0001F200-\U0001F2FF"  # 补充符号
    "✅❌⚠️🎉🛑🔒🔄⏳➕➖〰️"
    "]"
)

def clean_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    cleaned, count = EMOJI.subn("", content)
    if count:
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
    return count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python remove_emoji.py <文件1.py> [文件2.py ...]")
        sys.exit(1)
    total = 0
    for arg in sys.argv[1:]:
        n = clean_file(arg)
        if n:
            print(f"  {arg}: 删除 {n} 个表情")
        total += n
    print(f"共删除 {total} 个表情")
