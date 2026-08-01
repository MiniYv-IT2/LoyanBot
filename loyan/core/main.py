"""LoyanBot 启动入口 — 装配与生命周期编排

实例管理已拆至 loyan/core/runtime/manager.py。
本模块只做：日志/别名/信号初始化、lifecycle 驱动、欢迎横幅、主循环。
"""

import asyncio
import multiprocessing
try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass

from loyan.core.webserv import create_app, request, jsonify
import os
import sys
import time
import logging

from loyan.core.config import BOT_VERSION
from loyan.core.plugin_manager import plugin_manager
from loyan.core.utils import logger, logger_manager
from loyan.core.config_manager import config_manager
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanText
from loyan.core.lifecycle import lifecycle, LifecycleEvent

_lifecycle = lifecycle  # 全局单例（panel 等模块注册 hook 用同一个实例）

# ── 生命周期钩子注册 ──
async def _on_shutdown():
    await adapter_pool.stop_all()
_lifecycle.register_hook(LifecycleEvent.BEFORE_SHUTDOWN, _on_shutdown, "adapter_shutdown")



app = create_app()




def setup_error_handlers():

    @app.errorhandler(404)
    async def not_found(error):
        logger.warning(f'404 page not found from {request.remote_addr}: {request.method} {request.path}')
        return jsonify({"retcode": 404, "msg": "接口不存在"}), 404

    @app.errorhandler(405)
    async def method_not_allowed(error):
        logger.warning(f'405 method not allowed: {request.method} from {request.remote_addr}')
        return jsonify({"retcode": 405, "msg": "不支持的请求方法"}), 405

    @app.errorhandler(Exception)
    async def handle_exception(error):
        logger.critical(f'unhandled exception: {error}', exc_info=True)
        return jsonify({"retcode": 500, "msg": "服务器内部错误"}), 500





def safe_shutdown(signum=None, frame=None):


    try:
        default = adapter_pool.get_default()
        master_id = getattr(default, '_instance_master_id', '') if default else ''
        if master_id:
            shutdown_msg = f" 机器人正在关闭\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    loyan_send_msg(master_id, LoyanText(text=shutdown_msg), chat_type="private"),
                    loop
                )
    except Exception:
        pass


    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _lifecycle.fire_event_async(LifecycleEvent.BEFORE_SHUTDOWN), loop
            )
    except Exception:
        pass


    try:
        plugin_manager.shutdown()
    except Exception as e:
        logger.error(f"shutdown plugin manager failed: {e}")


    try:
        from loyan.core.monitor import monitor_manager
        monitor_manager.shutdown()
    except (ImportError, Exception) as e:
        if not isinstance(e, ImportError):
            logger.error(f"shutdown monitor failed: {e}")

    os._exit(0)




async def run_bot():
    from loyan.core.config import LOG_LEVEL, DEBUG_MODE
    logger_manager.setup_logging(log_level=LOG_LEVEL, debug_mode=DEBUG_MODE)

    import loyan.graci as _graci_pkg
    sys.modules.setdefault('graci', _graci_pkg)

    # 组合根：构建全局依赖容器并预构建（启动即暴露装配错误）
    from loyan.core.container import build_container, set_container
    container = build_container()
    container.build()
    set_container(container)

    try:
        from loyan.res.loyan_logo import LoyanBotLogo
        LoyanBotLogo().print_logo()
    except Exception:
        pass


    try:
        import signal
        signal.signal(signal.SIGTERM, safe_shutdown)
    except (ImportError, AttributeError):
        pass


    try:
        config_manager.load()
        await _lifecycle.fire_event_async(LifecycleEvent.AFTER_CONFIG_LOAD)
    except Exception as e:
        logger.error(f"config load failed: {str(e)}")


    try:
        plugin_manager.init()
        await plugin_manager.async_load()
        from loyan.core.loyan_session import loyan_init_session_manager
        await loyan_init_session_manager()
        await _lifecycle.fire_event_async(LifecycleEvent.AFTER_PLUGINS_LOADED)
    except Exception as e:
        logger.error(f"plugin manager init failed: {str(e)}")


    try:
        import loyan.brain  # 加载 AI 核心包（内部自注册 /chat 等内置指令 + 自启初始化）
    except Exception as e:
        logger.error(f"brain load failed: {e}")

    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_BRAIN_READY)


    from loyan.core.runtime.manager import init_instances
    await init_instances()

    try:
        import loyan.core.webserv.panel.server as _panel_server  # noqa: F401  面板自注册 lifecycle hook
    except Exception as e:
        logger.error(f"panel load failed: {e}")

    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_INSTANCES_READY)


    try:
        setup_error_handlers()
    except Exception as e:
        logger.error(f"error handlers setup failed: {e}")


    version_display = BOT_VERSION
    logger.info(f"====== LoyanBot v{version_display} 启动 ======")


    try:
        plugin_manager.trigger_on_ready()
    except Exception as e:
        logger.warning(f"on_ready hook failed: {e}")


    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_ADAPTERS_START)


    try:
        for adapter, _ in adapter_pool._adapters.values():
            adapter.register_routes(app)
    except Exception as e:
        logger.warning(f"route registration failed: {e}")


    if adapter_pool.count > 0:
        welcome_msg = f"🎉 LoyanBot v{version_display} 启动成功！\n"
        welcome_msg += f"📌 已加载 {plugin_manager.get_plugin_count()} 个插件"
        for tag in adapter_pool.all_tags:
            try:
                adapter = adapter_pool.get(tag)
                if not adapter:
                    continue
                targets = []
                mid = getattr(adapter, '_instance_master_id', '') or ''
                if mid:
                    targets.append(mid)
                admins = getattr(adapter, '_instance_admins_id', None) or []
                for uid in admins:
                    if uid not in targets:
                        targets.append(uid)
                if not targets:
                    continue
                for uid in targets:
                    asyncio.create_task(
                        loyan_send_msg(uid, LoyanText(text=welcome_msg), chat_type="private", tag=tag)
                    )
            except Exception:
                continue

    await _lifecycle.fire_event_async(LifecycleEvent.READY)


    http_port = config_manager.get("http_port", 0)
    if http_port:
        try:
            from loyan.core.webserv import run_server
            await run_server(app, http_port)
        except Exception as e:
            logger.critical(f"http server start failed: {str(e)}", exc_info=True)
            try:
                default = adapter_pool.get_default()
                master_id = getattr(default, '_instance_master_id', '') if default else ''
                if master_id:
                    asyncio.create_task(
                        loyan_send_msg(master_id, LoyanText(text=f" 机器人启动失败\n错误: {str(e)}"), chat_type="private")
                    )
            except Exception:
                pass
    else:

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            await adapter_pool.stop_all()
            logger.info("adapter pool stopped")

    os._exit(0)
