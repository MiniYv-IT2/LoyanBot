"""面板服务 — 启动/端口/重试"""

import asyncio
import threading
from typing import Optional

from loyan.core.lifecycle import lifecycle, LifecycleEvent
from loyan.core.webserv.quart import Config, serve
from loyan.core.webserv.panel import create_panel_app

_t: Optional[threading.Thread] = None


def get_panel_port() -> int:
    from loyan.core.webserv.panel.auth import get_port
    return get_port()


def _start():
    from loyan.core.webserv.panel.auth import get_port
    port = get_port()
    for attempt in range(3):
        try:
            app = create_panel_app()
            cfg = Config()
            cfg.bind = [f"0.0.0.0:{port}"]
            cfg.loglevel = "warning"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.add_signal_handler = lambda *_, **__: None

            loop.run_until_complete(serve(app, cfg))
            return
        except OSError:
            threading.Event().wait(2)
        except Exception:
            return


async def start_panel(context: dict | None = None):
    global _t
    if _t and _t.is_alive():
        return
    _t = threading.Thread(target=_start, daemon=True, name="LoyanUI-Quart")
    _t.start()
    _start_update_checker()


# ── 本体更新后台检查（启动 30s 后 + 按配置间隔，只检查不安装） ──

_update_task: asyncio.Task | None = None


def _start_update_checker():
    global _update_task
    if _update_task is not None and not _update_task.done():
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        return

    async def _loop():
        await asyncio.sleep(30)
        while True:
            try:
                from loyan.core.config_manager import config_manager
                from loyan.core.update_manager import update_manager
                if not config_manager.get("auto_update_core", False):
                    await asyncio.sleep(3600)
                    continue
                info = await update_manager.check()
                if info.get("available"):
                    _logger.info("new version available: v%s", info.get("latest"))
                await update_manager.close()
            except Exception as e:
                _logger.debug("update check skipped: %s", e)
            try:
                from loyan.core.config_manager import config_manager
                interval = max(1, int(config_manager.get("update_check_interval_hours", 24) or 24)) * 3600
            except Exception:
                interval = 24 * 3600
            await asyncio.sleep(interval)

    _update_task = loop.create_task(_loop())


async def _register_panel_commands(context: dict | None = None):
    """注册 /panel 内置命令（面板模块自注册，main 不感知）"""
    from loyan.core.pipeline.builtin_commands import register_builtin_command
    from loyan.core.webserv.panel.commands import handle_panel
    register_builtin_command("/panel", handle_panel, require_admin=True)


# 面板通过生命周期自注册：实例就绪后启动 + 注册命令
lifecycle.register_hook(LifecycleEvent.AFTER_INSTANCES_READY, start_panel, "panel_start")
lifecycle.register_hook(LifecycleEvent.AFTER_INSTANCES_READY, _register_panel_commands, "panel_commands")
