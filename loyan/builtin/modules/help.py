"""Help Command - /help /帮助 /菜单"""
import collections
import os
from graci import get_logger, on_command, plugin_handler, PluginContext, LoyanPaths
from graci import LoyanImage
from graci import plugin_manager, config_manager

logger = get_logger("Builtin.help")

paths = LoyanPaths("builtin")
_drawer = None


def _get_drawer():
    global _drawer
    if _drawer is None:
        config = config_manager.get_plugin("builtin")
        from .core.draw import LoyanBotHelpDrawer
        _drawer = LoyanBotHelpDrawer(config)
    return _drawer


@on_command("/help", "/帮助", "/菜单", "/helps")
@plugin_handler
async def handle_help(ctx: PluginContext):
    """生成帮助图片并发送"""
    from graci import plugin_manager
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
        image = _get_drawer().draw_help_image(dict(plugin_commands))
        temp_path = os.path.join(paths.data(), "temp_help.png")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        from PIL import Image
        img = Image.open(image)
        img.save(temp_path, "PNG")
        await ctx.reply(file=LoyanImage(temp_path))
    except Exception as e:
        logger.error(f"生成帮助图失败: {e}", exc_info=True)
        await ctx.reply("生成帮助图失败，请检查配置")
