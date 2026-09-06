"""Help Command - 帮助菜单（完整复刻原Help_plugin）"""
import collections
import logging
import io

import os
import textwrap
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.decorators.registration import on_command
from loyan.core.tools.paths import LoyanPaths
from loyan.core.loyan_adapter.message import LoyanImage
from loyan.core.plugin_manager import plugin_manager
from loyan.core.config_manager import config_manager


import logging
logger = logging.getLogger("Loyan.Builtin.help")

# 资源路径
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RES_DIR = os.path.join(_BASE_DIR, "res", "resource")
_FONT_PATH = os.path.join(_RES_DIR, "DouyinSansBold.otf")
_LOGO_PATH = os.path.join(_RES_DIR, "loyan_logo.png")

paths = LoyanPaths("builtin")
config_manager.register_plugin_config("帮助插件")


class LoyanBotHelpDrawer:
    """帮助图绘制器"""
    
    # ... (保持原有绘图逻辑不变)
    COLOR_BACKGROUND_START = (248, 250, 255)
    COLOR_BACKGROUND_END = (255, 252, 248)
    COLOR_SECTION_HEADER_BG = (240, 242, 248)
    COLOR_CARD_BACKGROUND = (255, 255, 255)
    COLOR_CARD_OUTLINE = (220, 225, 235)
    COLOR_TEXT_HEADER = (255, 182, 193)
    COLOR_TEXT_SUBTITLE = (80, 80, 80)
    COLOR_TEXT_PLUGIN = (255, 182, 193)
    COLOR_TEXT_COMMAND = (255, 182, 193)
    COLOR_TEXT_DESC = (70, 70, 70)
    COLOR_TEXT_FOOTER = (100, 100, 100)
    COLOR_ACCENT = (0, 90, 180)
    COLOR_LOGO_BG_REMOVE = (255, 255, 255)
    LOGO_BG_TOLERANCE = 25

    IMG_WIDTH = 800
    PADDING = 25
    TOP_AREA_HEIGHT = 120
    LOGO_TARGET_HEIGHT = 65
    SECTION_HEADER_HEIGHT = 50
    SECTION_MARKER_SIZE = 18
    SECTION_MARKER_PADDING = (SECTION_HEADER_HEIGHT - SECTION_MARKER_SIZE) // 2
    SECTION_TITLE_LEFT_MARGIN = SECTION_MARKER_PADDING * 2 + SECTION_MARKER_SIZE
    SECTION_SPACING_BELOW_HEADER = 15
    SECTION_SPACING_AFTER_CARDS = 25
    CARD_PADDING_X = 15
    CARD_SPACING = 12
    CARD_CORNER_RADIUS = 10
    CARD_INTERNAL_SPACE = 4
    FOOTER_HEIGHT = 40
    CARD_PADDING_TOP = 10
    CARD_PADDING_BOTTOM = 10
    NAME_DESC_SPACING = 12

    BUILT_IN_COMMANDS_TEXT = textwrap.dedent("""
        [System]
        /关于 : 查看关于LoyanBot的开发信息
        /系统更新 : 检测可用的最新框架版本
        /确认更新 : 选择开始系统更新
        /取消更新 : 取消系统更新操作
        /状态 : 获取基本的运行状态信息
        /重启 : 重启您的Bot
        /关机 : 让您的Bot得到充分休息
        /开机 : 执行开机命令
        /运行状态 : 查看框架运行信息及系统资源详情

        [AI对话]
        /+persona : 创建新的AI对话人设
        /-persona : 删除指定人设
        /persona : 切换到指定人设
    """).strip()

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}
        self._load_fonts()
        self._load_logo()

    def _load_fonts(self) -> None:
        try:
            self.font_title = ImageFont.truetype(_FONT_PATH, 36)
            self.font_subtitle = ImageFont.truetype(_FONT_PATH, 18)
            self.font_plugin_header = ImageFont.truetype(_FONT_PATH, 20)
            self.font_command = ImageFont.truetype(_FONT_PATH, 15)
            self.font_desc = ImageFont.truetype(_FONT_PATH, 13)
            self.font_footer = ImageFont.truetype(_FONT_PATH, 12)
        except Exception as e:
            logger.error(f"加载字体失败: {e}")
            raise

    def _load_logo(self) -> None:
        try:
            if not os.path.exists(_LOGO_PATH):
                self.resized_logo = None
                return
            logo_img = Image.open(_LOGO_PATH).convert("RGBA")
            img_data = np.array(logo_img)
            r, g, b, a = img_data.T
            white_areas = (
                (r >= self.COLOR_LOGO_BG_REMOVE[0] - self.LOGO_BG_TOLERANCE)
                & (g >= self.COLOR_LOGO_BG_REMOVE[1] - self.LOGO_BG_TOLERANCE)
                & (b >= self.COLOR_LOGO_BG_REMOVE[2] - self.LOGO_BG_TOLERANCE)
                & (a > 128)
            )
            img_data[..., -1][white_areas.T] = 0
            logo_transparent = Image.fromarray(img_data)
            ow, oh = logo_transparent.size
            new_w = int(self.LOGO_TARGET_HEIGHT * ow / oh)
            self.resized_logo = logo_transparent.resize(
                (new_w, self.LOGO_TARGET_HEIGHT), Image.Resampling.LANCZOS
            )
        except Exception as e:
            logger.warning(f"加载 Logo 失败: {e}")
            self.resized_logo = None

    @staticmethod
    def _parse_single_command_list(text_list) -> List[Tuple[str, Optional[str]]]:
        commands = []
        lines = (
            text_list.strip().splitlines()
            if isinstance(text_list, str)
            else [ln for ln in text_list if ln.strip()]
        )
        for line in lines:
            raw = line
            stripped = line.strip()
            if not stripped or (stripped.startswith("[") and stripped.endswith("]")):
                continue
            if (raw.startswith("  ") or raw.startswith("\t")) and commands:
                cmd, desc = commands[-1]
                commands[-1] = (cmd, (desc or "") + stripped)
                continue
            parts = None
            for sep in (" : ", " # ", "#", ":"):
                if sep in stripped:
                    parts = stripped.split(sep, 1)
                    break
            if parts and len(parts) == 2:
                cmd = (
                    parts[0][2:].strip()
                    if parts[0].startswith("- ")
                    else parts[0].strip()
                )
                desc = parts[1].strip()
            else:
                cmd = stripped[2:].strip() if stripped.startswith("- ") else stripped
                desc = None
            commands.append((cmd, desc))
        return [(c, (d.splitlines()[0].strip() if d else None)) for c, d in commands]

    def _parse_plugin_commands_sorted_grouped(
        self, plugin_dict: Dict[str, Any]
    ) -> List[Tuple[str, List[Tuple[str, Optional[str]]]]]:
        show_builtin = self.config.get("show_builtin_cmds", {}).get("default", False) \
            if isinstance(self.config.get("show_builtin_cmds"), dict) \
            else self.config.get("show_builtin_cmds", False)
        
        built_in_list = self._parse_single_command_list(self.BUILT_IN_COMMANDS_TEXT) if show_builtin else []
        built_in_plugin = ("内置指令", built_in_list) if built_in_list else None

        large_plugins, small_plugins = [], []
        plugin_blacklist = self.config.get("plugin_blacklist", {}).get("default", []) \
            if isinstance(self.config.get("plugin_blacklist"), dict) \
            else self.config.get("plugin_blacklist", [])

        for name, cmds_raw in plugin_dict.items():
            if name == "内置指令" or not cmds_raw:
                continue
            if name in plugin_blacklist:
                continue
            cmds = self._parse_single_command_list(cmds_raw)
            if not cmds:
                continue
            (small_plugins if len(cmds) == 1 else large_plugins).append((name, cmds))

        large_plugins.sort(key=lambda x: len(x[1]), reverse=True)

        grouped_small = None
        if small_plugins:
            all_small = [c for _, cmds in small_plugins for c in cmds]
            if all_small:
                grouped_small = ("简易指令", all_small)
                logger.info(f"-> 创建 '简易指令' ({len(all_small)} 条)")

        result = []
        if built_in_plugin:
            result.append(built_in_plugin)
        result.extend(large_plugins)
        if grouped_small:
            result.append(grouped_small)
        return result

    @staticmethod
    def _draw_gradient(draw, width: int, height: int, start: Tuple[int, ...], end: Tuple[int, ...]):
        for y in range(height):
            r = int(start[0] + (end[0] - start[0]) * y / height)
            g = int(start[1] + (end[1] - start[1]) * y / height)
            b = int(start[2] + (end[2] - start[2]) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    def _get_text_metrics(self, text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw):
        if not text:
            return (0, 0, 0, 0), (0, 0)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            return bbox, (w, h)
        except AttributeError:
            w = draw.textlength(text, font=font)
            h = sum(font.getmetrics()) if sum(font.getmetrics()) > 0 else font.size * 1.2
            return (0, 0, int(w), int(h)), (int(w), int(h))
        except Exception:
            est_w = len(text) * font.size * 0.6
            est_h = font.size * 1.2
            return (0, 0, max(1, int(est_w)), max(1, int(est_h))), (max(1, int(est_w)), max(1, int(est_h)))

    def _draw_rounded_rectangle(self, draw: ImageDraw.ImageDraw, xy, radius, fill=None, outline=None, width=1):
        x1, y1, x2, y2 = xy
        if x1 >= x2 or y1 >= y2:
            return
        radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        if fill:
            draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
            draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
            draw.pieslice((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=fill)
            draw.pieslice((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=fill)
            draw.pieslice((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=fill)
            draw.pieslice((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=fill)
        if outline and width > 0:
            draw.arc((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=outline, width=width)
            draw.arc((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=outline, width=width)
            draw.arc((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=outline, width=width)
            draw.arc((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=outline, width=width)
            draw.line([(x1 + radius, y1), (x2 - radius, y1)], fill=outline, width=width)
            draw.line([(x1 + radius, y2), (x2 - radius, y2)], fill=outline, width=width)
            draw.line([(x1, y1 + radius), (x1, y2 - radius)], fill=outline, width=width)
            draw.line([(x2, y1 + radius), (x2, y2 - radius)], fill=outline, width=width)

    def _layout_cards(self, sections: List[Tuple[str, List[Tuple[str, Optional[str]]]]], draw: ImageDraw.ImageDraw) -> List[Dict]:
        layout_info = []
        y_offset = self.TOP_AREA_HEIGHT + self.PADDING
        card_width = (self.IMG_WIDTH - self.PADDING * 2 - self.CARD_SPACING * 3) // 4

        for section_name, cmds in sections:
            layout_info.append({"type": "header", "name": section_name, "y": y_offset})
            y_offset += self.SECTION_HEADER_HEIGHT + self.SECTION_SPACING_BELOW_HEADER

            row_cards, col_idx, max_row_height = [], 0, 0
            for cmd, desc in cmds:
                _, (w_cmd, h_cmd) = self._get_text_metrics(cmd, self.font_command, draw)
                wrapped_desc = textwrap.wrap(desc or "", width=12)
                bbox = self.font_desc.getbbox("A")
                line_height = (bbox[3] - bbox[1]) + self.CARD_INTERNAL_SPACE
                h_desc_total = len(wrapped_desc) * line_height if wrapped_desc else 0
                card_h = max(
                    self.CARD_PADDING_TOP + h_cmd + self.NAME_DESC_SPACING + h_desc_total + self.CARD_PADDING_BOTTOM,
                    35
                )
                row_cards.append({"type": "card", "name": cmd, "desc": desc, "height": card_h})
                max_row_height = max(max_row_height, card_h)
                col_idx += 1

                if col_idx == 4:
                    for i, card in enumerate(row_cards):
                        card["x"] = self.PADDING + i * (card_width + self.CARD_SPACING)
                        card["y"] = y_offset
                        card["width"] = card_width
                    layout_info.extend(row_cards)
                    y_offset += max_row_height + self.CARD_SPACING
                    row_cards, col_idx, max_row_height = [], 0, 0

            if row_cards:
                for i, card in enumerate(row_cards):
                    card["x"] = self.PADDING + i * (card_width + self.CARD_SPACING)
                    card["y"] = y_offset
                    card["width"] = card_width
                layout_info.extend(row_cards)
                y_offset += max_row_height + self.CARD_SPACING

            y_offset += self.SECTION_SPACING_AFTER_CARDS
        return layout_info

    def _draw_cards(self, img: Image.Image, layout_info: List[Dict]) -> None:
        draw = ImageDraw.Draw(img)
        for item in layout_info:
            if item["type"] == "header":
                draw.rectangle(
                    (0, item["y"], self.IMG_WIDTH, item["y"] + self.SECTION_HEADER_HEIGHT),
                    fill=self.COLOR_SECTION_HEADER_BG
                )
                draw.ellipse(
                    (
                        self.SECTION_MARKER_PADDING, item["y"] + self.SECTION_MARKER_PADDING,
                        self.SECTION_MARKER_PADDING + self.SECTION_MARKER_SIZE,
                        item["y"] + self.SECTION_MARKER_PADDING + self.SECTION_MARKER_SIZE,
                    ),
                    fill=self.COLOR_ACCENT
                )
                draw.text(
                    (self.SECTION_TITLE_LEFT_MARGIN, item["y"] + self.SECTION_MARKER_PADDING),
                    item["name"], font=self.font_plugin_header, fill=self.COLOR_TEXT_HEADER
                )
            elif item["type"] == "card":
                x0, y0 = item["x"], item["y"]
                x1, y1 = x0 + item["width"], y0 + item["height"]
                self._draw_rounded_rectangle(
                    draw, (x0, y0, x1, y1), radius=self.CARD_CORNER_RADIUS,
                    fill=self.COLOR_CARD_BACKGROUND, outline=self.COLOR_CARD_OUTLINE, width=1
                )
                draw.text(
                    (x0 + self.CARD_PADDING_X, y0 + self.CARD_PADDING_TOP),
                    item["name"], font=self.font_command, fill=self.COLOR_TEXT_COMMAND
                )
                if item.get("desc"):
                    wrapped_desc = textwrap.wrap(item["desc"], width=12)
                    bbox_cmd = self.font_command.getbbox(item["name"])
                    y_start = y0 + self.CARD_INTERNAL_SPACE + (bbox_cmd[3] - bbox_cmd[1]) + self.NAME_DESC_SPACING
                    line_height = (self.font_desc.getbbox("A")[3] - self.font_desc.getbbox("A")[1]) + self.CARD_INTERNAL_SPACE
                    for i, line in enumerate(wrapped_desc):
                        draw.text(
                            (x0 + self.CARD_PADDING_X, y_start + i * line_height),
                            line, font=self.font_desc, fill=self.COLOR_TEXT_DESC
                        )

    def draw_help_image(self, plugin_commands_dict: Dict[str, Any]) -> bytes:
        sections = self._parse_plugin_commands_sorted_grouped(plugin_commands_dict)

        temp_img = Image.new("RGB", (self.IMG_WIDTH, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(temp_img)
        layout_info = self._layout_cards(sections, draw)
        total_height = (
            layout_info[-1]["y"]
            + (layout_info[-1]["height"] if "height" in layout_info[-1] else 0)
            + self.FOOTER_HEIGHT + self.PADDING
        )

        img = Image.new("RGB", (self.IMG_WIDTH, total_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        self._draw_gradient(draw, self.IMG_WIDTH, total_height, self.COLOR_BACKGROUND_START, self.COLOR_BACKGROUND_END)

        if self.resized_logo:
            img.paste(self.resized_logo, (self.PADDING, self.PADDING), self.resized_logo)
            title_text = "LoyanBot 帮助指南"
            subtitle_text = "可用插件及指令列表"
            logo_w, logo_h = self.resized_logo.size
            x_start = self.PADDING + logo_w + 15
            draw.text((x_start, self.PADDING), title_text, font=self.font_title, fill=self.COLOR_TEXT_HEADER)
            y_sub = self.PADDING + self.font_title.getbbox(title_text)[3] - self.font_title.getbbox(title_text)[1] + 5
            draw.text((x_start, y_sub), subtitle_text, font=self.font_subtitle, fill=self.COLOR_TEXT_SUBTITLE)

        self._draw_cards(img, layout_info)

        footer_text = "LoyanBot --致力于简洁体验的QQ框架"
        bbox = draw.textbbox((0, 0), footer_text, font=self.font_footer)
        fw, fh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (self.IMG_WIDTH - fw - self.PADDING, total_height - self.FOOTER_HEIGHT + (self.FOOTER_HEIGHT - fh) // 2),
            footer_text, font=self.font_footer, fill=self.COLOR_TEXT_FOOTER
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


_drawer = None


def _get_drawer() -> LoyanBotHelpDrawer:
    global _drawer
    if _drawer is None:
        config = config_manager.get_plugin("帮助插件")
        _drawer = LoyanBotHelpDrawer(config)
    return _drawer


@on_command("/help", "/帮助", "/菜单", "/helps")
@plugin_handler
async def handle_help(ctx: PluginContext):
    """生成帮助图片并发送"""
    # 直接访问 registry
    registry = plugin_manager.registry

    plugin_commands: Dict[str, list] = collections.defaultdict(list)
    for plugin in registry:
        name = plugin.get("name", "未知插件")
        if name == "帮助插件":
            continue
        desc = plugin.get("description", "")
        cmd_descs = plugin.get("command_descriptions", {})
        for cmd in plugin.get("commands", []):
            cmd_desc = cmd_descs.get(cmd, "") or desc
            plugin_commands[name].append(f"{cmd}#{cmd_desc}" if cmd_desc else cmd)

    if not plugin_commands:
        await ctx.reply("没有找到任何插件或命令")
        return

    try:
        image_data = _get_drawer().draw_help_image(dict(plugin_commands))
        temp_path = os.path.join(paths.data(), "temp_help.png")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(image_data)
        await ctx.send(LoyanImage(file_path=temp_path))
    except Exception as e:
        logger.error(f"生成帮助图片失败: {e}", exc_info=True)
        await ctx.reply("生成帮助图片失败，请联系管理员")
