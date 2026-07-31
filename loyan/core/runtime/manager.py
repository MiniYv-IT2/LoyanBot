"""实例管理 — 发现/注册/热重载/启停/重命名

从 core/main.py 拆出的实例域，面板 API 与启动流程共用。
公共 API（名称不变）：init_instances / reload_instance / start_instance / rename_instance / stop_instance
"""

import asyncio
import importlib
import json
import logging
import os

from loyan.core.config import BOT_VERSION
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.message import LoyanText
from loyan.core.runtime import Runtime, RuntimeRegistry
from loyan.core.tools.log_runtime import setup_runtime_logger
from loyan.core.pipeline import Pipeline, SecurityFilter, BuiltinCommands, CommandMatcher, PluginHandler, ResponseSender
from loyan.core.pipeline.stats_collector import stats_collector
from loyan.core.tools.paths import get_instances_dir
from loyan.core.event import event_bus
from loyan.core.plugin_manager import plugin_manager
from loyan.core.lifecycle import lifecycle, LifecycleEvent

_logger = logging.getLogger("Core.Instance")

_on_event_callback = None  # 运行时注入，供实例启动/热重载使用


def _instances_dir() -> str:
    return get_instances_dir()


def _discover_instance_configs() -> list[dict]:
    inst_dir = _instances_dir()
    if not os.path.isdir(inst_dir):
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
            _logger.error(f"invalid config: {entry} - {e}")

    return results


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
            _logger.warning(f"adapter module not found: {platform}")
            return None
        except Exception as e:
            _logger.error(f"create failed: {platform} - {e}")
            return None

    try:
        create_fn = getattr(module, "create_adapter")
        adapter = create_fn(cfg)
    except AttributeError:
        _logger.warning(f"adapter module missing create_adapter: {platform}")
        return None
    except Exception as e:
        _logger.error(f"create failed: {platform} - {e}")
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


async def _register_instance(cfg: dict, default: bool = False, runtime=None) -> None:
    result = await _create_and_prepare_adapter(cfg, runtime=runtime)
    if result is None:
        return
    adapter, tag = result
    adapter_pool.register(adapter, tag, default=default)
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", cfg.get("_dir_name", "unknown"))
    conn_type = getattr(adapter, 'conn_type_display', '') or ''
    _logger.info(f"[Adapter] {platform}/{bot_name} ({conn_type}) started")


async def init_instances() -> int:
    """启动时加载全部实例配置；返回成功注册数"""
    try:
        await stats_collector.init()
    except Exception:
        pass

    configs = _discover_instance_configs()
    if not configs:
        return 0

    loaded = 0
    failed: list[str] = []
    for idx, cfg in enumerate(configs):
        try:
            runtime = _build_runtime(cfg)
            RuntimeRegistry.register(runtime)
            await _register_instance(cfg, default=(idx == 0), runtime=runtime)
            loaded += 1
        except Exception as e:
            failed.append(f"{cfg.get('_dir_name', '?')}({type(e).__name__}: {e})")

    if failed:
        _logger.error(
            f"[InstanceManager] {len(failed)}/{len(configs)} instances failed to load: {'; '.join(failed)}"
        )
    return loaded


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
                _logger.warning(f"stop failed: {name} - {e}")

        if old_tag is not None:
            adapter_pool.unregister(old_tag)

        if _on_event_callback:
            try:
                await new_adapter.start(_on_event_callback)
            except Exception as e:
                _logger.error(f"start failed: {name} - {e}")
                return {"success": False, "error": f"start_failed: {e}"}

        adapter_pool.register(new_adapter, new_tag, default=was_default)

        for runtime in RuntimeRegistry.get_all():
            if runtime.instance_name == name:
                RuntimeRegistry.unregister(runtime)
                runtime.adapter_tag = new_tag
                RuntimeRegistry.register(runtime)
                break

        _logger.info(f"reload ok: {name}")
        return {"success": True}
    except Exception as e:
        _logger.error(f"reload failed: {name} - {e}")
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
                _logger.error(f"start failed: {name} - {e}")
                return {"success": False, "error": f"start_failed: {e}"}

        adapter_pool.register(adapter, tag)
        _logger.info(f"[Adapter] {tag.log_tag} started")
        return {"success": True}
    except Exception as e:
        _logger.error(f"start failed: {name} - {e}")
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
        _logger.warning(f"stop failed: {name} - {e}")
    adapter_pool.unregister(tag)
    for runtime in RuntimeRegistry.get_all():
        if runtime.instance_name == name:
            RuntimeRegistry.unregister(runtime)
            break
    return {"success": True}


# ── 生命周期接入：实例就绪后注册事件回调并启动适配器 ──

def _bind_event_callback() -> None:
    global _on_event_callback
    if _on_event_callback is None:
        _on_event_callback = lambda e: asyncio.create_task(event_bus.publish(e))


async def _start_all_adapters(context: dict | None = None) -> None:
    _bind_event_callback()
    try:
        await adapter_pool.start_all(_on_event_callback)
    except Exception:
        pass


lifecycle.register_hook(LifecycleEvent.AFTER_INSTANCES_READY, _start_all_adapters, "adapters_start")
