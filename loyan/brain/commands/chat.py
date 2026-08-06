"""Brain 对话命令（框架内置指令）"""

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.utils import logger
from loyan.brain import get_brain
from loyan.core.pipeline.builtin_commands import register_builtin_command

logger = logger.getChild("Brain.cmd")


@plugin_handler
async def handle_chat(ctx: PluginContext):
    """与 AI 对话：/chat <消息>"""
    text = ctx.raw_text[len(ctx.command):].strip()
    if not text:
        await ctx.reply("用法：{cmd} <消息>\n例：{cmd} 你好".format(cmd=ctx.command))
        return

    brain = get_brain()
    if not brain.ready:
        await ctx.reply(" " + "Brain 未初始化，请先配置模型提供商")
        return

    reply = await brain.chat.chat(message=text, session_id=ctx.sender_id)
    content = reply or " " + "未获取到回复"
    await ctx.reply(content)


@plugin_handler
async def handle_chat_reset(ctx: PluginContext):
    """重置当前对话会话"""
    brain = get_brain()
    await ctx.reply(" " + "对话已重置")
    logger.info(f"用户 {ctx.sender_id} 重置了对话")


# ── 框架内置指令注册（brain 是核心包，不经过插件系统） ──
register_builtin_command("/chat", handle_chat)
register_builtin_command("/ai", handle_chat)
register_builtin_command("/chat reset", handle_chat_reset)
