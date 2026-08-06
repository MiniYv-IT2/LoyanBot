"""Brain 对话命令（框架内置指令）"""

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.utils import logger
from loyan.brain import get_brain
from loyan.core.pipeline.builtin_commands import register_builtin_command
from loyan.core.loyan_session import (
    resolve_from_context,
    loyan_get_or_create_im_session,
    loyan_add_im_context,
    loyan_clear_im_session,
)

logger = logger.getChild("Brain.cmd")


async def _im_session(ctx: PluginContext):
    """按统一会话层获取当前消息的 IM 会话（含持久化 instance_id）"""
    tag = ctx.adapter_tag
    return await loyan_get_or_create_im_session(
        platform=tag.platform if tag else "",
        instance_id=tag.instance_id if tag else "",
        chat_type=ctx.chat_type,
        sender_id=ctx.sender_id,
        target_id=ctx.target_id,
    )


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

    session_id = resolve_from_context(ctx)
    session = await _im_session(ctx)
    await loyan_add_im_context(session, "user", text)
    reply = await brain.chat.chat(message=text, session_id=session_id)
    content = reply or " " + "未获取到回复"
    await loyan_add_im_context(session, "assistant", content)
    await ctx.reply(content)


@plugin_handler
async def handle_chat_reset(ctx: PluginContext):
    """重置当前对话会话"""
    session_id = resolve_from_context(ctx)
    if session_id:
        await loyan_clear_im_session(session_id)
    await ctx.reply(" " + "对话已重置")
    logger.info(f"user {ctx.sender_id} reset IM session {session_id}")


# ── 框架内置指令注册（brain 是核心包，不经过插件系统） ──
register_builtin_command("/chat", handle_chat)
register_builtin_command("/ai", handle_chat)
register_builtin_command("/chat reset", handle_chat_reset)
