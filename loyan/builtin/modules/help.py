"""Help Command - /help /帮助 /菜单"""
import collections
import os
from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.decorators.registration import on_command
from loyan.core.utils import logger
from loyan.core.tools.paths import LoyanPaths
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanImage
from loyan.core.plugin_manager import plugin_manager

logger = logger.getChild("Builtin.help")

paths = LoyanPaths("builtin")


class LoyanBotHelpDrawer:
    """帮助图绘制器（简化版）"""
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def draw_help_image(self, plugin_commands):
        """绘制帮助图并返回PNG数据"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return b""
        
        # 计算图片尺寸
        lines = []
        for name, cmds in plugin_commands.items():
            lines.append(f"[{name}]")
            for cmd in cmds[:5]:  # 每个插件最多显示5个命令
                lines.append(f"  {cmd}")
        
        line_height = 20
        padding = 20
        img_height = padding * 2 + len(lines) * line_height
        img_width = 400
        
        # 创建图片
        img = Image.new('RGB', (img_width, img_height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # 绘制标题
        draw.text((padding, padding), "LoyanBot 帮助", fill='#ffffff', font=title_font)
        
        # 绘制内容
        y = padding * 2
        for line in lines:
            if line.startswith('['):
                draw.text((padding, y), line, fill='#e94560', font=title_font)
            else:
                draw.text((padding, y), line, fill='#cccccc', font=font)
            y += line_height
        
        # 保存到内存
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


_drawer = None


def _get_drawer():
    global _drawer
    if _drawer is None:
        _drawer = LoyanBotHelpDrawer()
    return _drawer


@on_command("/help", "/帮助", "/菜单", "/helps")
@plugin_handler
async def handle_help(ctx: PluginContext):
    """生成帮助图片并发送"""
    plugin_commands = collections.defaultdict(list)
    for plugin in plugin_manager.registry:
        name = plugin.get("name", "未知插件")
        if name == "builtin":
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
        await loyan_send_msg(ctx.target_id, LoyanImage(temp_path), chat_type=ctx.chat_type)
    except Exception as e:
        logger.error(f"生成帮助图失败: {e}", exc_info=True)
        await ctx.reply("生成帮助图失败，请检查配置")
