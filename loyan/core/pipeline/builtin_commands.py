"""Stage: BuiltinCommands — 框架级内置命令（/关机, /重启, /开机, /关于）"""

import asyncio
import logging
import platform
import subprocess
import os
import sys
from typing import Optional

from loyan.core.pipeline import Stage
from loyan.core.decorators.context import PluginContext
from loyan.core.pipeline.helpers import is_master

_logger = logging.getLogger("Core.Pipeline")

# ── 框架内部注册的内置命令（插件开发者不可见） ──

_BUILTIN_COMMAND_REGISTRY: dict = {}
# 内置命令注册顺序（长命令优先，避免 /chat 吞掉 /chat reset）
_BUILTIN_COMMAND_ORDER: list[str] = []


def register_builtin_command(command: str, handler, *, require_admin: bool = False) -> None:
    """注册框架内部内置命令（仅限框架模块调用，不暴露给插件）

    支持带参数命令：/chat 注册后，"/chat xxx" 也会命中，
    精确匹配优先于前缀匹配，长命令优先于短命令。
    """
    if command not in _BUILTIN_COMMAND_REGISTRY:
        _BUILTIN_COMMAND_ORDER.append(command)
    _BUILTIN_COMMAND_REGISTRY[command] = {"handler": handler, "require_admin": require_admin}


def _match_builtin(raw_msg: str, prefix: str = "/") -> Optional[dict]:
    """匹配内置命令：先精确，后按注册顺序前缀匹配；支持前缀替换（/ 开头命令）"""
    entry = _BUILTIN_COMMAND_REGISTRY.get(raw_msg)
    if entry is not None:
        return entry
    for command in _BUILTIN_COMMAND_ORDER:
        if command.startswith("/"):
            variants = [prefix + command[1:]] if prefix and prefix != "/" else [command]
        else:
            variants = [command]
        for v in variants:
            if raw_msg == v or raw_msg.startswith(v + " "):
                return _BUILTIN_COMMAND_REGISTRY[command]
    return None


async def _dispatch_registered(ctx: PluginContext) -> Optional[PluginContext]:
    """分发注册表里的内置命令；命中返回 ctx（已消费），未命中返回 None"""
    raw_msg = ctx.raw_text.strip()
    prefix = "/"
    try:
        from loyan.core.config.user_config import get_effective_cached
        instance = getattr(getattr(ctx, "runtime", None), "instance_name", "") or ""
        prefix = get_effective_cached(instance).get("command_prefix", "/") or "/"
    except Exception:
        pass
    entry = _match_builtin(raw_msg, prefix)
    if entry is None:
        return None
    if entry["require_admin"] and not is_master(ctx):
        return ctx
    await entry["handler"](ctx)
    return ctx


class BuiltinCommands(Stage):
    """内置命令处理器

    处理 /关机, /重启, /开机, /关于 等框架级命令。
    """

    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        from loyan.core.config import BOT_VERSION
        from loyan.core.loyan_adapter.send import loyan_send_msg
        from loyan.core.loyan_adapter.message import LoyanText

        raw_msg = ctx.raw_text.strip()
        sender_id = str(ctx.sender_id)
        target_id = str(ctx.target_id)
        chat_type = ctx.chat_type
        is_master_user = is_master(ctx)

        prefix = "/"
        try:
            from loyan.core.config.user_config import get_effective_cached
            instance = getattr(getattr(ctx, "runtime", None), "instance_name", "") or ""
            prefix = get_effective_cached(instance).get("command_prefix", "/") or "/"
        except Exception:
            pass
        if prefix and prefix != "/":
            if raw_msg.startswith(prefix):
                canonical = "/" + raw_msg[len(prefix):]
            elif raw_msg.startswith("/"):
                canonical = ""
            else:
                canonical = raw_msg
        else:
            canonical = raw_msg

        from loyan.core.pipeline.helpers import inject_send_reply
        inject_send_reply(ctx)

        dispatched = await _dispatch_registered(ctx)
        if dispatched is not None:
            return dispatched

        if canonical == "/关机":
            if is_master_user:
                await loyan_send_msg(target_id, LoyanText(text=" 正在执行关机操作...机器人将在3秒后关闭"), chat_type=chat_type)
                _logger.info(f"[内置命令] 主人{sender_id}执行/关机命令")

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
                            _logger.info("[关机指令] systemd关机成功")
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
            else:
                await loyan_send_msg(target_id, LoyanText(text=" 权限不足！只有主人可以执行关机操作"), chat_type=chat_type)
                _logger.warning(f"[安全防护] 用户{sender_id}尝试关机，权限不足")
            return None

        if canonical == "/重启":
            if is_master_user:
                await loyan_send_msg(target_id, LoyanText(text=" 正在执行重启操作...机器人将在5秒后重启"), chat_type=chat_type)
                _logger.info(f"[内置命令] 主人{sender_id}执行/重启命令")

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
            else:
                await loyan_send_msg(target_id, LoyanText(text=" 权限不足！只有主人可以执行重启操作"), chat_type=chat_type)
                _logger.warning(f"[安全防护] 用户{sender_id}尝试重启，权限不足")
            return None

        if canonical == "/开机":
            if is_master_user:
                await loyan_send_msg(target_id, LoyanText(text=" 正在执行开机操作...机器人服务将在3秒后启动"), chat_type=chat_type)
                _logger.info(f"[内置命令] 主人{sender_id}执行/开机命令")

                async def delayed_startup():
                    await asyncio.sleep(3)
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            'systemctl', 'start', 'bot.service',
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        _, _ = await proc.communicate()
                        if proc.returncode == 0:
                            _logger.info("[开机指令] systemd启动成功")
                            return
                    except Exception:
                        pass
                    if platform.system() == "Windows":
                        subprocess.Popen(
                            [sys.executable] + sys.argv,
                            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                            close_fds=True,
                        )
                    else:
                        subprocess.Popen([sys.executable] + sys.argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    _logger.info("[开机指令] 新进程已启动")

                asyncio.ensure_future(delayed_startup())
            else:
                await loyan_send_msg(target_id, LoyanText(text=" 权限不足！只有主人可以执行开机操作"), chat_type=chat_type)
                _logger.warning(f"[安全防护] 用户{sender_id}尝试开机，权限不足")
            return None

        if canonical == "/关于":
            try:
                from loyan.core.loyan_adapter.pool import adapter_pool
                tags = adapter_pool.all_tags
                adapter_lines = [f"├ {t.platform}/{t.bot_name}{' (' + t.conn_type + ')' if t.conn_type else ''}" for t in tags]
                adapter_str = "\n".join(adapter_lines) if adapter_lines else "无"
            except Exception:
                adapter_str = "未知"

            try:
                from loyan.core.plugin_manager import plugin_manager
                plugin_count = len(plugin_manager.registry)
            except Exception:
                plugin_count = 0

            about_content = (
                f"LoyanBot v{BOT_VERSION}\n"
                f"├ 作者: 小禹\n"
                f"├ 定位: 跨平台 IM 轻量异步框架\n"
                f"├ 适配器:\n{adapter_str}\n"
                f"├ Python: {platform.python_version()}\n"
                f"├ 插件: {plugin_count} 个已注册\n"
                f"└ 联系: QQ 192004908\n"
                f"\n/帮助 查看所有命令"
            )
            await loyan_send_msg(target_id, LoyanText(text=about_content), chat_type=chat_type)
            _logger.info(f"[内置命令] 用户{sender_id}执行/关于命令")
            return None

        return ctx
