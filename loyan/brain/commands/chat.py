"""Brain 对话命令（框架内置指令）"""

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.utils import logger
from loyan.brain import get_brain
from loyan.i18n import t
from loyan.core.pipeline.builtin_commands import register_builtin_command

logger = logger.getChild("Brain.cmd")


@plugin_handler
async def handle_chat(ctx: PluginContext):
    """与 AI 对话：/chat <消息>"""
    text = ctx.raw_text[len(ctx.command):].strip()
    if not text:
        await ctx.reply(t("command.chat_usage_full", cmd=ctx.command))
        return

    brain = get_brain()
    if not brain.ready:
        await ctx.reply(" " + t("chat.brain_not_ready"))
        return

    reply = await brain.chat.chat(message=text, session_id=ctx.sender_id)
    content = reply or " " + t("chat.no_reply")
    await ctx.reply(content)


@plugin_handler
async def handle_chat_reset(ctx: PluginContext):
    """重置当前对话会话"""
    brain = get_brain()
    await ctx.reply(" " + t("chat.session_reset"))
    logger.info(f"用户 {ctx.sender_id} 重置了对话")


# ── 框架内置指令注册（brain 是核心包，不经过插件系统） ──
register_builtin_command("/chat", handle_chat)
register_builtin_command("/ai", handle_chat)
register_builtin_command("/chat reset", handle_chat_reset)
