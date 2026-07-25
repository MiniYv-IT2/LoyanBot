"""Brain 对话命令"""

from loyan.graci import on_command, plugin_handler, PluginContext, get_logger
from loyan.brain import get_brain
from loyan.i18n import t
from loyan.core.decorators.registration import _register_decorated_function, DECORATOR_COMMAND_REGISTRY

logger = get_logger("Brain.cmd")


@on_command("/chat", "/ai")
@plugin_handler
async def handle_chat(ctx: PluginContext):
    """与 AI 对话：/chat <消息>"""
    text = ctx.raw_text[len(ctx.command):].strip()
    if not text:
        await ctx.reply(t("command.chat_usage_full", cmd=ctx.command))
        return

    brain = get_brain()
    if not brain.ready:
        await ctx.reply("❌ " + t("chat.brain_not_ready"))
        return

    reply = await brain.chat.chat(message=text, session_id=ctx.sender_id)
    content = reply or "❌ " + t("chat.no_reply")
    await ctx.reply(content)


@on_command("/chat reset")
@plugin_handler
async def handle_chat_reset(ctx: PluginContext):
    """重置当前对话会话"""
    brain = get_brain()
    await ctx.reply("✅ " + t("chat.session_reset"))
    logger.info(f"用户 {ctx.sender_id} 重置了对话")


# ── 模块导入时自动注册 ──
for _name, _obj in list(globals().items()):
    if hasattr(_obj, "_loyan_on_command"):
        _register_decorated_function(_obj, plugin_name="brain")
