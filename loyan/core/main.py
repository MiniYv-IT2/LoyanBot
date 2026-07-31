
import asyncio
import multiprocessing
try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass

from loyan.core.webserv import create_app, request, jsonify
import importlib
import json
import os
import threading
import time
import sys
import traceback
import logging

from loyan.core.config import BOT_VERSION
from loyan.core.plugin_manager import plugin_manager
from loyan.core.utils import logger, logger_manager
from loyan.core.config_manager import config_manager
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanText
from loyan.core.event import event_bus
from loyan.core.runtime import Runtime, RuntimeRegistry
from loyan.core.tools.log_runtime import setup_runtime_logger
from loyan.core.pipeline import Pipeline, SecurityFilter, BuiltinCommands, CommandMatcher, PluginHandler, ResponseSender
from loyan.core.pipeline.stats_collector import stats_collector
from loyan.core.tools.paths import get_instances_dir, get_project_root
from loyan.core.lifecycle import lifecycle, LifecycleEvent

_lifecycle = lifecycle  # 全局单例（panel 等模块注册 hook 用同一个实例）
_on_event_callback = None  # 运行时注入，供热重载使用

# ── 生命周期钩子注册 ──
async def _on_shutdown():
    await adapter_pool.stop_all()
_lifecycle.register_hook(LifecycleEvent.BEFORE_SHUTDOWN, _on_shutdown, "adapter_shutdown")



app = create_app()




def _instances_dir() -> str:
    return get_instances_dir()


def _discover_instance_configs() -> list[dict]:

    inst_dir = _instances_dir()
    if not os.path.isdir(inst_dir):
        logger.warning(f" 实例目录不存在: {inst_dir}")
        return []

    results = []
    for entry in sorted(os.listdir(inst_dir)):
        cfg_path = os.path.join(inst_dir, entry, "config.json")
        if not os.path.isfile(cfg_path):
            continue
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                continue
            cfg["_dir_name"] = entry
            cfg["_config_path"] = cfg_path
            results.append(cfg)
        except Exception as e:
            logger.error(f" 加载实例配置失败 {cfg_path}: {e}")

    return results


async def _register_instance(cfg: dict, default: bool = False, runtime=None) -> None:
    result = await _create_and_prepare_adapter(cfg, runtime=runtime)
    if result is None:
        return
    adapter, tag = result
    adapter_pool.register(adapter, tag, default=default)
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", cfg.get("_dir_name", "unknown"))
    conn_type = getattr(adapter, 'conn_type_display', '') or ''
    master_id = adapter._instance_master_id or ""
    logger.info(f"   [{tag.log_tag}] {platform}/{bot_name} ({conn_type}) master={master_id[:4]}****")


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
        logger.error(f" 关闭插件管理器异常: {e}")


    try:
        from loyan.core.monitor import monitor_manager
        monitor_manager.shutdown()
    except (ImportError, Exception) as e:
        if not isinstance(e, ImportError):
            logger.error(f" 关闭监控管理器异常: {e}")

    os._exit(0)


def _build_runtime(cfg: dict) -> Runtime:
    """根据实例配置构建 Runtime（含 Pipeline）"""
    instance_name = cfg.get("_dir_name", "unknown")
    robot_id = cfg.get("robot_id", "")
    master_id = cfg.get("master_id", "")
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", instance_name)
    tag = IdentityTag(platform=platform, bot_name=bot_name)
    runtime = Runtime(
        instance_name=instance_name,
        robot_id=robot_id,
        master_id=master_id,
        adapter_tag=tag,
        plugin_manager=plugin_manager,
        adapter_pool=adapter_pool,
    )
    pipeline = Pipeline()
    pipeline.add_stage(SecurityFilter())
    pipeline.add_stage(BuiltinCommands())
    pipeline.add_stage(CommandMatcher())
    pipeline.add_stage(PluginHandler())
    pipeline.add_stage(ResponseSender())
    pipeline.add_stage(stats_collector)
    runtime.pipeline = pipeline
    runtime.logger = setup_runtime_logger(instance_name, bot_name=bot_name)
    return runtime


async def _init_instances() -> None:

    try:
        await stats_collector.init()
    except Exception:
        pass

    configs = _discover_instance_configs()
    if not configs:
        logger.warning(" 未发现任何实例配置（storage/instances/<name>/config.json）")
        return

    for idx, cfg in enumerate(configs):
        try:
            instance_name = cfg.get("_dir_name", f"instance_{idx}")
            runtime = _build_runtime(cfg)

            RuntimeRegistry.register(runtime)


            await _register_instance(cfg, default=(idx == 0), runtime=runtime)

        except Exception as e:
            logger.error(f" 初始化实例失败 {cfg.get('_dir_name', '?')}: {e}")

    count = adapter_pool.count


# ── 公共 API：热重载 ──

async def _create_and_prepare_adapter(cfg: dict, runtime=None):
    """根据配置创建适配器实例，返回 (adapter, tag) 或 None"""
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", cfg.get("_dir_name", "unknown"))
    robot_id = runtime.robot_id if runtime else cfg.get("robot_id", "")
    master_id = runtime.master_id if runtime else cfg.get("master_id", "")
    tag = runtime.adapter_tag if runtime else IdentityTag(platform=platform, bot_name=bot_name)

    try:
        module = importlib.import_module(f"loyan.core.loyan_adapter.platform.{platform}.adapter")
    except ImportError:
        try:
            module = importlib.import_module(f"core.loyan_adapter.platform.{platform}.adapter")
        except ImportError:
            logger.warning(f" 无法加载适配器模块: {platform}（实例 {cfg.get('_dir_name', '?')}），跳过")
            return None
        except Exception as e:
            logger.error(f" 创建适配器实例失败 {platform}: {e}")
            return None

    try:
        create_fn = getattr(module, "create_adapter")
        adapter = create_fn(cfg)
    except AttributeError:
        logger.warning(f" 适配器 {platform} 缺少 create_adapter 工厂函数，跳过")
        return None
    except Exception as e:
        logger.error(f" 创建适配器实例失败 {platform}: {e}")
        return None

    adapter.tag = tag
    adapter._instance_master_id = master_id
    adapter._instance_admins_id = cfg.get("admins_id", None) or []
    if not master_id and adapter._instance_admins_id:
        adapter._instance_master_id = adapter._instance_admins_id[0]
    adapter._instance_robot_id = robot_id
    adapter._runtime = runtime

    conn_type = getattr(adapter, 'conn_type_display', '') or ''
    if conn_type:
        tag.conn_type = conn_type

    return adapter, tag


async def reload_instance(name: str) -> dict:
    """热重载指定实例：停旧启新"""
    cfg_path = os.path.join(get_instances_dir(), name, "config.json")
    if not os.path.isfile(cfg_path):
        return {"success": False, "error": "not_found"}
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_dir_name"] = name
    cfg["_config_path"] = cfg_path

    old_adapter = None
    old_tag = None
    for adp, tg in adapter_pool._adapters.values():
        if tg.bot_name == name or tg.identity_key.endswith(f"/{name}"):
            old_adapter = adp
            old_tag = tg
            break

    try:
        result = await _create_and_prepare_adapter(cfg)
        if result is None:
            return {"success": False, "error": "create_failed"}
        new_adapter, new_tag = result

        was_default = (old_tag is not None and
                       adapter_pool._default_key == old_tag.identity_key)

        if old_adapter is not None:
            try:
                await old_adapter.stop()
            except Exception as e:
                logger.warning(f" 停止旧适配器失败 {name}: {e}")

        if old_tag is not None:
            adapter_pool.unregister(old_tag)

        if _on_event_callback:
            try:
                await new_adapter.start(_on_event_callback)
            except Exception as e:
                logger.error(f" 启动新适配器失败 {name}: {e}")
                return {"success": False, "error": f"start_failed: {e}"}

        adapter_pool.register(new_adapter, new_tag, default=was_default)

        from loyan.core.runtime import RuntimeRegistry, RuntimeContext
        for runtime in RuntimeRegistry.get_all():
            if runtime.instance_name == name:
                RuntimeRegistry.unregister(runtime)
                runtime.adapter_tag = new_tag
                RuntimeRegistry.register(runtime)
                break

        logger.info(f"  热重载完成: {name}")
        return {"success": True}
    except Exception as e:
        logger.error(f" 热重载失败 {name}: {e}")
        return {"success": False, "error": str(e)}


async def start_instance(name: str) -> dict:
    """启动新创建的实例"""
    cfg_path = os.path.join(get_instances_dir(), name, "config.json")
    if not os.path.isfile(cfg_path):
        return {"success": False, "error": "not_found"}
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_dir_name"] = name
    cfg["_config_path"] = cfg_path

    try:
        from loyan.core.runtime import RuntimeRegistry

        runtime = None
        robot_id = cfg.get("robot_id", "")
        if robot_id:
            runtime = RuntimeRegistry.get_by_robot_id(robot_id)
        if runtime is None:
            for r in RuntimeRegistry.get_all():
                if r.instance_name == name:
                    runtime = r
                    break
        if runtime is None:
            runtime = _build_runtime(cfg)
            RuntimeRegistry.register(runtime)
        else:
            RuntimeRegistry.unregister(runtime)
            runtime.adapter_tag = IdentityTag(platform=cfg.get("platform", ""), bot_name=cfg.get("bot_name", name))
            RuntimeRegistry.register(runtime)

        result = await _create_and_prepare_adapter(cfg, runtime=runtime)
        if result is None:
            return {"success": False, "error": "create_failed"}
        adapter, tag = result

        if _on_event_callback:
            try:
                await adapter.start(_on_event_callback)
            except Exception as e:
                logger.error(f" 启动适配器失败 {name}: {e}")
                return {"success": False, "error": f"start_failed: {e}"}

        adapter_pool.register(adapter, tag)
        logger.info(f"  实例已启动: {name}")
        return {"success": True}
    except Exception as e:
        logger.error(f" 启动实例失败 {name}: {e}")
        return {"success": False, "error": str(e)}


async def rename_instance(old_name: str, new_name: str) -> dict:
    """重命名实例目录并热重载"""
    old_dir = os.path.join(get_instances_dir(), old_name)
    new_dir = os.path.join(get_instances_dir(), new_name)
    if not os.path.isdir(old_dir):
        return {"success": False, "error": "not_found"}
    if os.path.isdir(new_dir):
        return {"success": False, "error": "name_conflict"}
    await stop_instance(old_name)
    try:
        os.rename(old_dir, new_dir)
    except Exception as e:
        return {"success": False, "error": str(e)}
    start_result = await start_instance(new_name)
    return start_result


async def stop_instance(name: str) -> dict:
    """停止并注销指定实例"""
    target = None
    for adp, tg in adapter_pool._adapters.values():
        if tg.bot_name == name or tg.identity_key.endswith(f"/{name}"):
            target = (adp, tg)
            break
    if target is None:
        return {"success": False, "error": "not_running"}
    adapter, tag = target
    try:
        await adapter.stop()
    except Exception as e:
        logger.warning(f" 停止适配器失败 {name}: {e}")
    adapter_pool.unregister(tag)
    from loyan.core.runtime import RuntimeRegistry
    for runtime in RuntimeRegistry.get_all():
        if runtime.instance_name == name:
            RuntimeRegistry.unregister(runtime)
            break
    logger.info(f"  实例已停止: {name}")
    return {"success": True}


async def run_bot():
    from loyan.core.config import LOG_LEVEL, DEBUG_MODE
    logger_manager.setup_logging(log_level=LOG_LEVEL, debug_mode=DEBUG_MODE)

    import loyan.graci as _graci_pkg
    sys.modules.setdefault('graci', _graci_pkg)

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
        logger.error(f" 配置加载失败: {str(e)}")


    try:
        plugin_manager.init()
        await plugin_manager.async_load()
        from loyan.core.loyan_session import loyan_init_session_manager
        await loyan_init_session_manager()
        await _lifecycle.fire_event_async(LifecycleEvent.AFTER_PLUGINS_LOADED)
    except Exception as e:
        logger.error(f" 插件管理器初始化失败: {str(e)}")


    import loyan.brain
    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_BRAIN_READY)


    await _init_instances()

    try:
        import loyan.core.webserv.panel.server as _panel_server  # noqa: F401  面板自注册 lifecycle hook
    except Exception as e:
        logger.error(f"Panel load failed: {e}")

    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_INSTANCES_READY)


    try:
        setup_error_handlers()
    except Exception as e:
        logger.error(f"错误处理器设置失败: {e}")


    version_display = BOT_VERSION
    logger.info(f"====== LoyanBot v{version_display} 启动 ======")
    instance_count = adapter_pool.count

    default = adapter_pool.get_default()
    show_master = ""
    if default:
        mid = getattr(default, '_instance_master_id', '') or ''
        if not mid:
            admins = getattr(default, '_instance_admins_id', None) or []
            if admins:
                mid = admins[0]
        if mid:
            show_master = f"{mid[:4]}****" if len(mid) > 4 else mid
    logger.info(f"  已注册 | 管理员 ID:{show_master}")



    try:
        plugin_manager.trigger_on_ready()
    except Exception as e:
        logger.warning(f" on_ready 钩子触发失败: {e}")


    global _on_event_callback
    _on_event_callback = lambda e: asyncio.create_task(event_bus.publish(e))
    try:
        await adapter_pool.start_all(_on_event_callback)
    except Exception:
        pass
    await _lifecycle.fire_event_async(LifecycleEvent.AFTER_ADAPTERS_START)


    try:
        for adapter, _ in adapter_pool._adapters.values():
            adapter.register_routes(app)
    except Exception as e:
        logger.warning(f" 路由注册异常: {e}")


    if adapter_pool.count == 0:
        logger.warning(" 未配置任何实例")
    else:
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
                    logger.warning(" 未配置管理员，跳过启动消息发送")
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
            logger.critical(f" HTTP 服务启动失败: {str(e)}", exc_info=True)
            try:
                default = adapter_pool.get_default()
                master_id = getattr(default, '_instance_master_id', '') if default else ''
                if master_id:
                    asyncio.create_task(
                        loyan_send_msg(master_id, LoyanText(text=f" 机器人启动失败\n错误: {str(e)}"), chat_type="private")
                    )
            except:
                pass
    else:

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            await adapter_pool.stop_all()
            logger.info(" 适配器池已停止")

    os._exit(0)
