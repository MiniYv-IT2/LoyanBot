"""实例管理 — 发现/注册/热重载/启停/重命名

从 core/main.py 拆出的实例域，面板 API 与启动流程共用。
公共 API（名称不变）：init_instances / reload_instance / start_instance / rename_instance / stop_instance

结构：
    - InstanceManager：生产级类，构造注入 pool/registry/plugin_manager/event_bus
      （每实例操作锁 + 显式状态机 + reload 失败回滚）
    - 模块级兼容层：_instance = InstanceManager(全局单例)，模块级函数转发到 _instance
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

# 模块级默认依赖（兼容层 _instance 使用；类方法显式注入，不依赖这些别名）
_module_plugin_manager = plugin_manager
_module_adapter_pool = adapter_pool


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


def _build_runtime(cfg: dict, plugin_manager=None, adapter_pool=None) -> Runtime:
    """根据实例配置构建 Runtime（含 Pipeline）"""
    instance_name = cfg.get("_dir_name", "unknown")
    robot_id = cfg.get("robot_id", "")
    master_id = cfg.get("master_id", "")
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", instance_name)
    tag = IdentityTag(platform=platform, bot_name=bot_name)
    pm = plugin_manager if plugin_manager is not None else _module_plugin_manager
    ap = adapter_pool if adapter_pool is not None else _module_adapter_pool
    runtime = Runtime(
        instance_name=instance_name,
        robot_id=robot_id,
        master_id=master_id,
        adapter_tag=tag,
        plugin_manager=pm,
        adapter_pool=ap,
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


def _merge_adapter_schema_defaults(platform: str, cfg: dict) -> dict:
    """实例配置缺字段时用适配器 schema 默认值补全（schema 为默认值唯一来源）"""
    try:
        from loyan.core.config_manager import deep_merge_config
        schema = _load_platform_schema(platform)
        if not schema:
            return cfg
        defaults = {key: info.get("default") for key, info in schema.items()}
        return deep_merge_config(defaults, cfg)
    except Exception:
        return cfg


def _load_platform_schema(platform: str) -> dict | None:
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "loyan_adapter", "source", f"{platform}.schema_conf.json",
    )
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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
        adapter = create_fn(_merge_adapter_schema_defaults(platform, cfg))
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


async def _register_instance(cfg: dict, default: bool = False, runtime=None, pool=None) -> None:
    result = await _create_and_prepare_adapter(cfg, runtime=runtime)
    if result is None:
        return
    adapter, tag = result
    target = pool if pool is not None else _module_adapter_pool
    target.register(adapter, tag, default=default)
    platform = cfg.get("platform", "")
    bot_name = cfg.get("bot_name", cfg.get("_dir_name", "unknown"))
    conn_type = getattr(adapter, 'conn_type_display', '') or ''
    _logger.info(f"[Adapter] {platform}/{bot_name} ({conn_type}) started")


# ──────────────────────────────────────────────────────────────
# InstanceManager — 生产级实例管理器（构造注入）
# ──────────────────────────────────────────────────────────────

class InstanceManager:
    """实例管理器：发现/注册/热重载/启停/重命名

    构造注入 pool / registry / plugin_manager / event_bus，不依赖全局单例，
    便于单测替换为 Fake。每实例一把 asyncio.Lock，串行化 reload/start/stop/rename；
    显式状态机（stopped/starting/running/stopping/error）供健康检查。
    """

    def __init__(self, pool, registry, plugin_manager, event_bus):
        self._pool = pool
        self._registry = registry
        self._plugin_manager = plugin_manager
        self._event_bus = event_bus
        self._locks: dict[str, asyncio.Lock] = {}
        self._states: dict[str, str] = {}
        self._event_callback = None

    # ── 锁与状态 ──

    def _lock(self, name: str) -> asyncio.Lock:
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    def state(self, name: str) -> str:
        """查询实例状态（stopped/starting/running/stopping/error）"""
        return self._states.get(name, "stopped")

    # ── 事件回调 ──

    def set_event_callback(self, cb) -> None:
        """注入事件回调（适配器启动时用）；None 时回退到 event_bus.publish"""
        self._event_callback = cb

    def _get_event_callback(self):
        if self._event_callback is not None:
            return self._event_callback
        return lambda e: asyncio.create_task(self._event_bus.publish(e))

    async def _emit(self, event_name: str, payload: dict) -> None:
        """发送业务事件（事件类型延迟导入，失败不影响主流程）

        事件类型定义在 event/types.py（另一模块负责），运行时才导入。
        """
        try:
            from loyan.core.event import EventType, BusinessEvent
            await self._event_bus.publish_business(
                BusinessEvent(type=getattr(EventType, event_name), payload=payload, source="instance_manager")
            )
        except Exception as e:
            _logger.error(f"emit {event_name} failed: {e}")

    # ── 池/注册表辅助 ──

    def _find_in_pool(self, name: str):
        """按实例名查找 (adapter, tag)，找不到返回 (None, None)"""
        for tag in self._pool.all_tags:
            if tag.bot_name == name or tag.identity_key.endswith(f"/{name}"):
                return self._pool.get(tag), tag
        return None, None

    def _is_default(self, tag) -> bool:
        if tag is None:
            return False
        default_tag = self._pool.get_default_tag()
        return default_tag is not None and default_tag.identity_key == tag.identity_key

    def _update_runtime_tag(self, name: str, tag) -> None:
        """更新注册表中该实例 runtime 的 adapter_tag"""
        for runtime in self._registry.get_all():
            if runtime.instance_name == name:
                self._registry.unregister(runtime)
                runtime.adapter_tag = tag
                self._registry.register(runtime)
                break

    async def _rollback(self, name: str, old_adapter, old_tag, was_default: bool) -> bool:
        """reload 失败回滚：恢复旧适配器注册与旧 runtime tag，保证机器人不掉线"""
        if old_adapter is None or old_tag is None:
            self._states[name] = "error"
            return False
        restored = False
        try:
            if self._pool.get(old_tag) is None:
                self._pool.register(old_adapter, old_tag, default=was_default)
                try:
                    await old_adapter.start(self._get_event_callback())
                except Exception as e:
                    _logger.warning(f"rollback start failed: {name} - {e}")
            restored = True
        except Exception as e:
            _logger.error(f"rollback failed: {name} - {e}")
        self._update_runtime_tag(name, old_tag)
        self._states[name] = "running" if restored else "error"
        return restored

    # ── 公共操作 ──

    async def init_instances(self) -> int:
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
            name = cfg.get("_dir_name", "?")
            try:
                runtime = _build_runtime(cfg, plugin_manager=self._plugin_manager, adapter_pool=self._pool)
                self._registry.register(runtime)
                await _register_instance(cfg, default=(idx == 0), runtime=runtime, pool=self._pool)
                self._states[name] = "running"
                loaded += 1
            except Exception as e:
                self._states[name] = "error"
                failed.append(f"{name}({type(e).__name__}: {e})")

        if failed:
            _logger.error(
                f"[InstanceManager] {len(failed)}/{len(configs)} instances failed: {'; '.join(failed)}"
            )
        return loaded

    async def reload(self, name: str) -> dict:
        """热重载指定实例：停旧启新；失败回滚旧适配器，机器人不掉线"""
        async with self._lock(name):
            self._states[name] = "starting"
            cfg_path = os.path.join(get_instances_dir(), name, "config.json")
            if not os.path.isfile(cfg_path):
                self._states[name] = "error"
                await self._emit("INSTANCE_ERROR", {"name": name, "error": "not_found"})
                return {"success": False, "error": "not_found"}
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["_dir_name"] = name
            cfg["_config_path"] = cfg_path

            old_adapter, old_tag = self._find_in_pool(name)
            was_default = self._is_default(old_tag)

            try:
                result = await _create_and_prepare_adapter(cfg)
                if result is None:
                    self._states[name] = "error"
                    await self._emit("INSTANCE_ERROR", {"name": name, "error": "create_failed"})
                    return {"success": False, "error": "create_failed"}
                new_adapter, new_tag = result

                if old_adapter is not None:
                    try:
                        await old_adapter.stop()
                    except Exception as e:
                        _logger.warning(f"stop failed: {name} - {e}")

                if old_tag is not None:
                    self._pool.unregister(old_tag)

                try:
                    await new_adapter.start(self._get_event_callback())
                except Exception as e:
                    _logger.error(f"start failed: {name} - {e}")
                    restored = await self._rollback(name, old_adapter, old_tag, was_default)
                    if restored:
                        await self._emit("INSTANCE_RELOADED", {
                            "name": name,
                            "tag": old_tag.identity_key if old_tag else "",
                            "success": False,
                        })
                    else:
                        await self._emit("INSTANCE_ERROR", {"name": name, "error": f"start_failed: {e}"})
                    return {"success": False, "error": f"start_failed: {e}"}

                self._pool.register(new_adapter, new_tag, default=was_default)
                self._update_runtime_tag(name, new_tag)
                self._states[name] = "running"
                _logger.info(f"reload ok: {name}")
                await self._emit("INSTANCE_RELOADED", {
                    "name": name,
                    "tag": new_tag.identity_key if new_tag else "",
                    "success": True,
                })
                return {"success": True}
            except Exception as e:
                _logger.error(f"reload failed: {name} - {e}")
                restored = await self._rollback(name, old_adapter, old_tag, was_default)
                if restored:
                    await self._emit("INSTANCE_RELOADED", {
                        "name": name,
                        "tag": old_tag.identity_key if old_tag else "",
                        "success": False,
                    })
                else:
                    await self._emit("INSTANCE_ERROR", {"name": name, "error": str(e)})
                return {"success": False, "error": str(e)}

    async def start(self, name: str) -> dict:
        async with self._lock(name):
            return await self._start_unlocked(name)

    async def _start_unlocked(self, name: str) -> dict:
        """启动新创建的实例（假设已持有该实例锁）"""
        self._states[name] = "starting"
        cfg_path = os.path.join(get_instances_dir(), name, "config.json")
        if not os.path.isfile(cfg_path):
            self._states[name] = "error"
            return {"success": False, "error": "not_found"}
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["_dir_name"] = name
        cfg["_config_path"] = cfg_path

        try:
            runtime = None
            robot_id = cfg.get("robot_id", "")
            if robot_id:
                runtime = self._registry.get_by_robot_id(robot_id)
            if runtime is None:
                for r in self._registry.get_all():
                    if r.instance_name == name:
                        runtime = r
                        break
            if runtime is None:
                runtime = _build_runtime(cfg, plugin_manager=self._plugin_manager, adapter_pool=self._pool)
                self._registry.register(runtime)
            else:
                self._registry.unregister(runtime)
                runtime.adapter_tag = IdentityTag(platform=cfg.get("platform", ""), bot_name=cfg.get("bot_name", name))
                self._registry.register(runtime)

            result = await _create_and_prepare_adapter(cfg, runtime=runtime)
            if result is None:
                self._states[name] = "error"
                return {"success": False, "error": "create_failed"}
            adapter, tag = result

            try:
                await adapter.start(self._get_event_callback())
            except Exception as e:
                _logger.error(f"start failed: {name} - {e}")
                self._states[name] = "error"
                return {"success": False, "error": f"start_failed: {e}"}

            self._pool.register(adapter, tag)
            self._states[name] = "running"
            _logger.info(f"[Adapter] {tag.log_tag} started")
            await self._emit("INSTANCE_STARTED", {
                "name": name,
                "tag": tag.identity_key,
                "platform": tag.platform,
            })
            return {"success": True}
        except Exception as e:
            _logger.error(f"start failed: {name} - {e}")
            self._states[name] = "error"
            return {"success": False, "error": str(e)}

    async def rename(self, old_name: str, new_name: str) -> dict:
        """重命名实例目录并热重载（stop → os.rename → start）"""
        async with self._lock(old_name):
            old_dir = os.path.join(get_instances_dir(), old_name)
            new_dir = os.path.join(get_instances_dir(), new_name)
            if not os.path.isdir(old_dir):
                return {"success": False, "error": "not_found"}
            if os.path.isdir(new_dir):
                return {"success": False, "error": "name_conflict"}
            await self._stop_unlocked(old_name)
            try:
                os.rename(old_dir, new_dir)
            except Exception as e:
                return {"success": False, "error": str(e)}
            return await self._start_unlocked(new_name)

    async def stop(self, name: str) -> dict:
        async with self._lock(name):
            return await self._stop_unlocked(name)

    async def _stop_unlocked(self, name: str) -> dict:
        """停止并注销指定实例（假设已持有该实例锁）"""
        self._states[name] = "stopping"
        adapter, tag = self._find_in_pool(name)
        if adapter is None or tag is None:
            self._states[name] = "stopped"
            return {"success": False, "error": "not_running"}
        try:
            await adapter.stop()
        except Exception as e:
            _logger.warning(f"stop failed: {name} - {e}")
        self._pool.unregister(tag)
        for runtime in self._registry.get_all():
            if runtime.instance_name == name:
                self._registry.unregister(runtime)
                break
        self._states[name] = "stopped"
        await self._emit("INSTANCE_STOPPED", {
            "name": name,
            "tag": tag.identity_key,
        })
        return {"success": True}


# ──────────────────────────────────────────────────────────────
# 模块级兼容层 — 用全局单例装配，对外 API 名称/参数/返回结构不变
# ──────────────────────────────────────────────────────────────

_instance = InstanceManager(adapter_pool, RuntimeRegistry, plugin_manager, event_bus)

_on_event_callback = None  # 运行时注入，供实例启动/热重载使用


def set_event_callback(cb) -> None:
    """注入事件回调（模块级，同时同步到 _instance）"""
    global _on_event_callback
    _on_event_callback = cb
    _instance.set_event_callback(cb)


async def init_instances() -> int:
    """启动时加载全部实例配置；返回成功注册数"""
    return await _instance.init_instances()


async def reload_instance(name: str) -> dict:
    """热重载指定实例：停旧启新；失败回滚旧适配器"""
    return await _instance.reload(name)


async def start_instance(name: str) -> dict:
    """启动新创建的实例"""
    return await _instance.start(name)


async def rename_instance(old_name: str, new_name: str) -> dict:
    """重命名实例目录并热重载"""
    return await _instance.rename(old_name, new_name)


async def stop_instance(name: str) -> dict:
    """停止并注销指定实例"""
    return await _instance.stop(name)


# ── 生命周期接入：实例就绪后注册事件回调并启动适配器 ──

def _bind_event_callback() -> None:
    global _on_event_callback
    if _on_event_callback is None:
        _on_event_callback = lambda e: asyncio.create_task(event_bus.publish(e))
    _instance.set_event_callback(_on_event_callback)


async def _start_all_adapters(context: dict | None = None) -> None:
    _bind_event_callback()
    try:
        await adapter_pool.start_all(_on_event_callback)
    except Exception:
        pass


lifecycle.register_hook(LifecycleEvent.AFTER_INSTANCES_READY, _start_all_adapters, "adapters_start")
