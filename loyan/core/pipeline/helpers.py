"""Pipeline 通用辅助函数"""

from typing import Optional

from loyan.core.decorators.context import PluginContext

_logger = __import__("logging").getLogger("Core.Pipeline")


def inject_send_reply(ctx: PluginContext) -> None:
    """注入 ctx.send / ctx.reply（幂等，已注入则跳过）

    供 Pipeline 各阶段共用：内置指令在 BuiltinCommands 阶段直接执行，
    PluginHandler 在插件执行前注入，两者都需要 send/reply 工具。
    """
    if ctx.send is not None and ctx.reply is not None:
        return
    from loyan.core.loyan_adapter.send import loyan_send_msg
    from loyan.core.loyan_adapter.message import LoyanText

    if ctx.send is None:
        async def _send(*segs, ct=None):
            return await loyan_send_msg(
                ctx.target_id, *segs, chat_type=ct or ctx.chat_type,
                tag=ctx.adapter_tag,
            )
        ctx.send = _send
    if ctx.reply is None:
        async def _reply(text):
            return await loyan_send_msg(
                ctx.target_id, LoyanText(text=text), chat_type=ctx.chat_type,
                tag=ctx.adapter_tag,
            )
        ctx.reply = _reply


def _get_adapter(ctx: PluginContext):
    if ctx.pool and ctx.adapter_tag:
        return ctx.pool.get(ctx.adapter_tag)
    return None


def is_master(ctx: PluginContext, plugin: dict = None) -> bool:
    return is_admin(ctx)


def is_admin(ctx: PluginContext, plugin: dict = None) -> bool:
    sender_id = str(ctx.sender_id)

    # 检查 runtime 的 master_id
    if ctx.runtime and str(ctx.runtime.master_id) == sender_id:
        return True

    # 检查适配器实例的 master_id（兼容旧配置）
    adapter = _get_adapter(ctx)
    if adapter:
        inst_master = getattr(adapter, '_instance_master_id', None)
        if inst_master and str(inst_master) == sender_id:
            return True

    # 检查适配器实例的 admins 列表
    if adapter:
        inst_admins = getattr(adapter, '_instance_admins_id', None) or []
        if sender_id in inst_admins:
            return True

    # 全局 MASTER_ID 兜底
    try:
        from loyan.core.config import MASTER_ID
        if MASTER_ID and str(MASTER_ID) == sender_id:
            return True
    except Exception:
        pass

    return False
