import logging
"""System Commands - /关机 /重启"""
import asyncio
import platform
import subprocess
import os
import sys
from loyan.core.decorators.handler import plugin_handler
from loyan.core.decorators.context import PluginContext
from loyan.core.pipeline.builtin_commands import register_builtin_command
from loyan.core.utils import logger
from loyan.core.pipeline.helpers import is_master
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanText


logger = logging.getLogger("Builtin.system")


@plugin_handler
async def handle_shutdown(ctx: PluginContext):
    """执行关机操作"""
    if not is_master(ctx):
        await loyan_send_msg(ctx.target_id, LoyanText("权限不足！只有主人可以执行关机操作"), chat_type=ctx.chat_type)
        return
    await loyan_send_msg(ctx.target_id, LoyanText("正在执行关机操作...机器人将在3秒后关闭"), chat_type=ctx.chat_type)
    async def delayed_shutdown():
        await asyncio.sleep(3)
        try:
            proc = await asyncio.create_subprocess_exec(
                'systemctl', 'stop', 'bot.service',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await proc.communicate()
            if proc.returncode == 0:
                return
        except Exception:
            pass
        try:
            from loyan.core.main import safe_shutdown
            safe_shutdown()
            return
        except ImportError:
            pass
        os._exit(0)
    asyncio.ensure_future(delayed_shutdown())


@plugin_handler
async def handle_restart(ctx: PluginContext):
    """执行重启操作"""
    if not is_master(ctx):
        await loyan_send_msg(ctx.target_id, LoyanText("权限不足！只有主人可以执行重启操作"), chat_type=ctx.chat_type)
        return
    await loyan_send_msg(ctx.target_id, LoyanText("正在执行重启操作...机器人将在5秒后重启"), chat_type=ctx.chat_type)
    async def delayed_restart():
        await asyncio.sleep(5)
        if platform.system() == "Windows":
            subprocess.Popen(
                [sys.executable] + sys.argv,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        else:
            subprocess.Popen(
                [sys.executable] + sys.argv,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        await asyncio.sleep(1)
        os._exit(0)
    asyncio.ensure_future(delayed_restart())


register_builtin_command("/关机", handle_shutdown, require_admin=True)
register_builtin_command("/重启", handle_restart, require_admin=True)
