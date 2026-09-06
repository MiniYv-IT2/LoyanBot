import logging
"""About Command - /关于"""
from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.pipeline.builtin_commands import register_builtin_command
from loyan.core.utils import logger
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanText
from loyan.core.config import BOT_VERSION
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.plugin_manager import plugin_manager


import logging
logger = logging.getLogger("Loyan.Builtin.about")


@plugin_handler
async def handle_about(ctx: PluginContext):
    """显示关于信息"""
    try:
        tags = adapter_pool.all_tags
        adapter_lines = [f"├ {t.platform}/{t.bot_name}{' (' + t.conn_type + ')' if t.conn_type else ''}" for t in tags]
        adapter_str = "\n".join(adapter_lines) if adapter_lines else "无"
    except Exception:
        adapter_str = "未知"

    try:
        plugin_count = len(plugin_manager.registry)
    except Exception:
        plugin_count = 0

    about_content = (
        f"LoyanBot v{BOT_VERSION}\n"
        f"├ 作者: 小禹\n"
        f"├ 定位: 跨平台 IM 轻量异步框架\n"
        f"├ 适配器:\n{adapter_str}\n"
        f"├ Python: {'.'.join(str(x) for x in __import__('sys').version_info[:2])}\n"
        f"├ 插件: {plugin_count} 个已注册\n"
        f"└ 联系: QQ 192004908\n"
        f"\n/帮助 查看所有命令"
    )
    await loyan_send_msg(ctx.target_id, LoyanText(text=about_content), chat_type=ctx.chat_type)


# ── 框架内置指令注册 ──
register_builtin_command("/关于", handle_about)
register_builtin_command("/about", handle_about)
register_builtin_command("/About", handle_about)
