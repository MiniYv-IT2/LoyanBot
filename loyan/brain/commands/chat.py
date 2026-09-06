"""Brain 对话命令（框架内置指令）"""

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.decorators.registration import on_fallback, _register_fallback_function
from loyan.core.utils import logger
from loyan.brain import get_brain
from loyan.core.pipeline.builtin_commands import register_builtin_command
from loyan.core.loyan_session import (
    resolve_from_context,
    loyan_get_or_create_im_session,
    loyan_add_im_context,
    loyan_clear_im_session,
)

import logging
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
    """与 AI 对话：/chat <消息>（带工具调用）"""
    text = ctx.raw_text[len(ctx.command):].strip()
    if not text:
        await ctx.reply("用法：{cmd} <消息>\n例：{cmd} 你好".format(cmd=ctx.command))
        return

    brain = get_brain()
    if not brain.ready:
        await ctx.reply(" " + "Brain 未初始化，请先配置模型提供商")
        return

    from loyan.brain.tools.agent import LoyanAgent
    session_id = resolve_from_context(ctx)
    session = await _im_session(ctx)
    agent = LoyanAgent(brain.chat)
    reply = await agent.chat_with_tools(
        message=text,
        session_id=session_id,
        ctx=ctx,
    )
    content = reply or " " + "未获取到回复"
    await loyan_add_im_context(session, "user", text)
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


@on_fallback()
@plugin_handler
async def handle_ai_fallback(ctx: PluginContext):
    """未匹配消息兜底: 私聊直接聊; 群聊必须 @机器人; 带前缀未匹配的指令静默"""
    if ctx.chat_type != "private":
        if ctx.chat_type != "group":
            return
        if not ctx.is_at_bot:
            return
    # 带前缀的消息 = 指令意图，未匹配指令则静默，不走 AI
    from loyan.core.config.user_config import get_effective_cached
    instance = getattr(getattr(ctx, "runtime", None), "instance_name", "") or ""
    prefix = get_effective_cached(instance).get("command_prefix", "/") or "/"
    if prefix and (ctx.raw_text or "").strip().startswith(prefix):
        return
    from loyan.brain import get_brain
    from loyan.brain.tools.agent import LoyanAgent
    brain = get_brain()
    if not brain.ready:
        return
    agent = LoyanAgent(brain.chat)
    session = await _im_session(ctx)
    text = ctx.text or ctx.raw_text or ""
    reply = await agent.chat_with_tools(
        message=text,
        session_id=resolve_from_context(ctx),
        ctx=ctx,
    )
    if reply:
        await loyan_add_im_context(session, "user", text)
        await loyan_add_im_context(session, "assistant", reply)
        from loyan.core.loyan_adapter.send import loyan_send_msg
        from loyan.core.loyan_adapter.message import LoyanText
        await loyan_send_msg(ctx.target_id, LoyanText(text=reply), chat_type=ctx.chat_type, tag=ctx.adapter_tag)


# ── 框架内置指令注册（brain 是核心包，不经过插件系统） ──
register_builtin_command("/chat", handle_chat)
register_builtin_command("/ai", handle_chat)
register_builtin_command("/chat reset", handle_chat_reset)

# 私聊 + 群聊兜底注册（群聊由 handle_ai_fallback 内部 @ 闸门约束）
_register_fallback_function(handle_ai_fallback, plugin_name="brain", chat_type=["private", "group"])
