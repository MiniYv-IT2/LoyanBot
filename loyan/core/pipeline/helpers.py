"""Pipeline 通用辅助函数"""

from typing import Optional

from loyan.core.decorators.context import PluginContext

_logger = __import__("logging").getLogger("Core.Pipeline")


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
