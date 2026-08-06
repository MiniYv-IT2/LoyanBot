"""人设命令（框架内置指令）"""

from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.utils import logger
from loyan.brain.chat.persona import persona_mgr
from loyan.core.pipeline.builtin_commands import register_builtin_command

logger = logger.getChild("Brain.cmd")


@plugin_handler
async def handle_persona(ctx: PluginContext):
    args = ctx.raw_text[len("/persona"):].strip().split(maxsplit=2)
    cmd = args[0] if args else ""

    if cmd == "list" or not cmd:
        personas = await persona_mgr.list()
        current = persona_mgr.current
        lines = ["📋 人设列表（当前: {current}）".format(current=current)]
        for p in personas:
            mark = " 👈" if p.name == current else ""
            prompt_short = p.prompt[:30] + "..." if len(p.prompt) > 30 else p.prompt
            lines.append(f"  {p.name}{mark}: {prompt_short}")
        await ctx.reply("\n".join(lines))
        return

    if cmd == "set" and len(args) >= 2:
        name = args[1]
        p = await persona_mgr.get(name)
        if not p:
            await ctx.reply("❌ 人设「{name}」不存在".format(name=name))
            return
        persona_mgr.set_current(name)
        await ctx.reply("✅ 已切换至「{name}」".format(name=name))
        return

    if cmd == "create" and len(args) >= 3:
        name = args[1]
        prompt = args[2]
        ok = await persona_mgr.create(name, prompt)
        if ok:
            await ctx.reply("✅ 人设「{name}」已创建".format(name=name))
        else:
            await ctx.reply("❌ 创建失败，可能名称已存在")
        return

    if cmd == "delete" and len(args) >= 2:
        name = args[1]
        ok = await persona_mgr.delete(name)
        if ok:
            await ctx.reply("✅ 已删除「{name}」".format(name=name))
        else:
            await ctx.reply("❌ 不能删除默认人设或人设不存在")
        return

    await ctx.reply("用法：/persona list | set <名称> | create <名称> <提示词> | delete <名称>")


# ── 框架内置指令注册（brain 是核心包，不经过插件系统） ──
register_builtin_command("/persona", handle_persona)
