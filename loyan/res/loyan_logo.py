"""LoyanBot 启动 Logo — 从 logo_art.py 导入纯字符画，在此文件上色渲染
更换 Logo 只需替换 loyan/res/logo_art.py 中的 ASCII_ART 即可，无需改动此文件。
"""

import sys
import re
import urllib.request
import json

from .logo_art import ASCII_ART


class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    ORANGE = '\033[38;5;208m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'


_COLOR_CYCLE = [
    '\033[38;5;66m',      # 深雾青
    '\033[38;5;73m',      # 雾青绿
    '\033[38;5;80m',      # 中雾青
    '\033[38;5;116m',     # 浅海绿
    '\033[38;5;152m',     # 雾青（主色）
    '\033[38;5;159m',     # 亮青
    '\033[38;5;189m',     # 淡薰衣草
]


class LoyanBotLogo:
    def __init__(self):
        self.colors = Colors()

    def _colorize(self, text: str, color: str) -> str:
        return f"{color}{text}{self.colors.RESET}"

    def _get_logo(self) -> list[str]:
        lines = ASCII_ART.strip('\n').split('\n')
        logo_lines = []
        for line in lines:
            colored = ""
            glyph_pos = 0
            in_glyph = False
            for ch in line:
                if ch == ' ':
                    colored += ch
                    in_glyph = False
                else:
                    if not in_glyph:
                        glyph_pos = 0
                        in_glyph = True
                    color = _COLOR_CYCLE[glyph_pos % len(_COLOR_CYCLE)]
                    colored += self._colorize(ch, color)
                    glyph_pos += 1
            logo_lines.append(colored)
        logo_lines.append("")
        return logo_lines

    @staticmethod
    def _strip_ansi(text: str) -> str:
        return re.sub(r'\033\[[0-9;]*m', '', text)

    def print_logo(self) -> None:
        logo = self._get_logo()
        is_tty = sys.stdout.isatty()
        for line in logo:
            print(self._strip_ansi(line) if not is_tty else line)

        print("")
        cat_text = "喵，Loyan酱被主人召回成功了喵(=^･ω･^=)"
        dev_info = "最好用的Bot框架 开发者QQ:192004908 小禹"
        if is_tty:
            print(f"\033[95m{cat_text}\033[0m")
            print(f"\033[35m{dev_info}\033[0m")
        else:
            print(cat_text)
            print(dev_info)

        hitokoto = None
        try:
            req = urllib.request.Request(
                "https://v1.hitokoto.cn/?c=j",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                hitokoto = data.get("hitokoto", "")
        except Exception:
            pass

        if hitokoto:
            pink = "\033[38;5;213m"
            reset = "\033[0m"
            if is_tty:
                print(f"{pink}{hitokoto}{reset}")
            else:
                print(hitokoto)


if __name__ == "__main__":
    LoyanBotLogo().print_logo()
