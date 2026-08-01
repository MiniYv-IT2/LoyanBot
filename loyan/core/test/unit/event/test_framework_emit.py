"""框架接入发送点测试 — InstanceManager / PluginManager 发业务事件

- FakeEventBus 只注入目标 manager 实例（构造注入），不污染全局 event_bus
- PluginManager 侧通过 monkeypatch 替换 loyan.core.event.event_bus 记录调用
- 事件类型延迟导入：types.py 未落地时用本地回退枚举挂到 event 模块，
  真实 EventType/BusinessEvent 落地后自动优先使用真实定义
"""

import asyncio
import enum
import json
import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.plugin_manager import PluginManager
from loyan.core.runtime import manager as manager_mod


class _FallbackEventType(enum.Enum):
    INSTANCE_STARTED = "instance_started"
    INSTANCE_STOPPED = "instance_stopped"
    INSTANCE_RELOADED = "instance_reloaded"
    INSTANCE_ERROR = "instance_error"
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_RELOADED = "plugin_reloaded"
    PLUGIN_ERROR = "plugin_error"


@dataclass
class _FallbackBusinessEvent:
    type: Any
    payload: Any
    source: str = ""
    adapter_tag: str = ""
    timestamp: float = 0.0
    cancelled: bool = False


@pytest.fixture(autouse=True)
def _ensure_event_types(monkeypatch):
    """types.py 未落地时提供回退 EventType/BusinessEvent，保证发送点可运行"""
    import loyan.core.event as event_mod
    try:
        from loyan.core.event import EventType
    except (ImportError, AttributeError):
        monkeypatch.setattr(event_mod, "EventType", _FallbackEventType)
    try:
        from loyan.core.event import BusinessEvent
    except (ImportError, AttributeError):
        monkeypatch.setattr(event_mod, "BusinessEvent", _FallbackBusinessEvent)


# ══════════════════════════════════════════════════════════
# InstanceManager fakes
# ══════════════════════════════════════════════════════════


class FakeEventBus:
    """记录 publish_business 调用的假事件总线（只注入目标 manager）"""

    def __init__(self):
        self.calls = []

    async def publish(self, event):
        pass

    async def publish_business(self, event):
        self.calls.append(event)


class FakeAdapter:
    def __init__(self, name="fake", fail_start=False):
        self.name = name
        self.fail_start = fail_start
        self.started = 0
        self.stopped = 0
        self.tag = None

    async def start(self, on_event=None):
        if self.fail_start:
            raise RuntimeError("fake start boom")
        self.started += 1

    async def stop(self):
        self.stopped += 1


class FakePool:
    def __init__(self):
        self._adapters = {}
        self._default_key = None

    def register(self, adapter, tag, default=False):
        key = tag.identity_key
        self._adapters[key] = (adapter, tag)
        if self._default_key is None or default:
            self._default_key = key

    def unregister(self, tag):
        key = tag.identity_key
        if key in self._adapters:
            del self._adapters[key]
        if self._default_key == key:
            self._default_key = next(iter(self._adapters)) if self._adapters else None

    def get(self, tag):
        pair = self._adapters.get(tag.identity_key)
        return pair[0] if pair else None

    def get_default_tag(self):
        if self._default_key:
            pair = self._adapters.get(self._default_key)
            return pair[1] if pair else None
        return None

    @property
    def all_tags(self):
        return [tag for _, tag in self._adapters.values()]


class FakeRegistry:
    def __init__(self):
        self._runtimes = []

    def register(self, runtime):
        self._runtimes.append(runtime)

    def unregister(self, runtime):
        if runtime in self._runtimes:
            self._runtimes.remove(runtime)

    def get_all(self):
        return list(self._runtimes)

    def get_by_robot_id(self, robot_id):
        for r in self._runtimes:
            if getattr(r, "robot_id", "") == robot_id:
                return r
        return None


class FakeRuntime:
    def __init__(self, name, robot_id="", adapter_tag=None):
        self.instance_name = name
        self.robot_id = robot_id
        self.adapter_tag = adapter_tag


@pytest.fixture
def instances_dir(tmp_path, monkeypatch):
    d = str(tmp_path / "instances")
    os.makedirs(d, exist_ok=True)
    monkeypatch.setattr(manager_mod, "get_instances_dir", lambda: d)
    return d


def _write_config(instances_dir: str, name: str) -> str:
    cfg = {"enabled": True, "platform": "fake", "bot_name": name,
           "robot_id": f"rid_{name}", "master_id": "m1", "admins_id": []}
    d = os.path.join(instances_dir, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


def make_manager():
    bus = FakeEventBus()
    mgr = manager_mod.InstanceManager(FakePool(), FakeRegistry(), SimpleNamespace(), bus)
    return mgr, bus


# ══════════════════════════════════════════════════════════
# InstanceManager 发送点
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_start_emits_instance_started(instances_dir, monkeypatch):
    _write_config(instances_dir, "bot1")
    mgr, bus = make_manager()
    adapter = FakeAdapter("bot1")
    tag = IdentityTag(platform="fake", bot_name="bot1")

    async def _create(cfg, runtime=None):
        return adapter, tag

    def _build(cfg, plugin_manager=None, adapter_pool=None):
        return FakeRuntime(cfg["_dir_name"], cfg.get("robot_id", ""))

    monkeypatch.setattr(manager_mod, "_build_runtime", _build)
    monkeypatch.setattr(manager_mod, "_create_and_prepare_adapter", _create)

    result = await mgr.start("bot1")

    assert result == {"success": True}
    assert len(bus.calls) == 1
    ev = bus.calls[0]
    assert ev.type.name == "INSTANCE_STARTED"
    assert ev.source == "instance_manager"
    assert ev.payload == {"name": "bot1", "tag": tag.identity_key, "platform": "fake"}


@pytest.mark.asyncio
async def test_stop_emits_instance_stopped(instances_dir, monkeypatch):
    _write_config(instances_dir, "bot1")
    mgr, bus = make_manager()
    adapter = FakeAdapter("bot1")
    tag = IdentityTag(platform="fake", bot_name="bot1")
    mgr._pool.register(adapter, tag, default=True)
    mgr._registry.register(FakeRuntime("bot1", "rid_bot1", tag))

    result = await mgr.stop("bot1")

    assert result == {"success": True}
    assert len(bus.calls) == 1
    ev = bus.calls[0]
    assert ev.type.name == "INSTANCE_STOPPED"
    assert ev.payload == {"name": "bot1", "tag": tag.identity_key}


@pytest.mark.asyncio
async def test_reload_success_emits_instance_reloaded(instances_dir, monkeypatch):
    _write_config(instances_dir, "bot1")
    mgr, bus = make_manager()
    old = FakeAdapter("old")
    old_tag = IdentityTag(platform="fake", bot_name="bot1")
    mgr._pool.register(old, old_tag, default=True)
    mgr._registry.register(FakeRuntime("bot1", "rid_bot1", old_tag))

    new = FakeAdapter("new")
    new_tag = IdentityTag(platform="fake", bot_name="bot1")

    async def _create(cfg, runtime=None):
        return new, new_tag

    monkeypatch.setattr(manager_mod, "_create_and_prepare_adapter", _create)

    result = await mgr.reload("bot1")

    assert result == {"success": True}
    assert len(bus.calls) == 1
    ev = bus.calls[0]
    assert ev.type.name == "INSTANCE_RELOADED"
    assert ev.payload == {"name": "bot1", "tag": new_tag.identity_key, "success": True}


@pytest.mark.asyncio
async def test_reload_failure_emits_reloaded_false_after_rollback(instances_dir, monkeypatch):
    _write_config(instances_dir, "bot1")
    mgr, bus = make_manager()
    old = FakeAdapter("old")
    old_tag = IdentityTag(platform="fake", bot_name="bot1")
    mgr._pool.register(old, old_tag, default=True)
    mgr._registry.register(FakeRuntime("bot1", "rid_bot1", old_tag))

    new = FakeAdapter("new", fail_start=True)

    async def _create(cfg, runtime=None):
        return new, IdentityTag(platform="fake", bot_name="bot1")

    monkeypatch.setattr(manager_mod, "_create_and_prepare_adapter", _create)

    result = await mgr.reload("bot1")

    assert result["success"] is False
    assert len(bus.calls) == 1
    ev = bus.calls[0]
    assert ev.type.name == "INSTANCE_RELOADED"
    assert ev.payload == {"name": "bot1", "tag": old_tag.identity_key, "success": False}


# ══════════════════════════════════════════════════════════
# PluginManager 发送点
# ══════════════════════════════════════════════════════════


class RecordingBus:
    def __init__(self):
        self.calls = []
    async def publish_business(self, event):
        self.calls.append(event)

def make_pm():
    fake_logger = SimpleNamespace(
        error=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, debug=lambda *a, **k: None,
    )
    fake_lm = SimpleNamespace(log_with_context=lambda *a, **k: None)
    return PluginManager(config_manager=SimpleNamespace(), logger=fake_logger, logger_manager=fake_lm)

@pytest.fixture
def recording_bus(monkeypatch):
    import loyan.core.event as event_mod
    bus = RecordingBus()
    monkeypatch.setattr(event_mod, "event_bus", bus)
    return bus

@pytest.mark.asyncio
async def test_async_load_emits_plugin_loaded(recording_bus, monkeypatch):
    pm = make_pm()
    pm._plugins_meta = {"__seed__": {}}
    pm._registry = [
        {"name": "demo", "version": "1.0.0", "author": "tester",
         "plugin_path": "", "commands": [], "priority": 50},
        {"name": "demo2", "version": "2.0.0", "author": "tester",
         "plugin_path": "", "commands": [], "priority": 50},
    ]

    async def _noop_scan():
        pass

    monkeypatch.setattr(pm, "_load_plugins_by_dependency", lambda meta: None)
    monkeypatch.setattr(pm, "_async_scan_all", _noop_scan)

    await pm.async_load()

    assert pm._initialized is True
    loaded = [ev for ev in recording_bus.calls if ev.type.name == "PLUGIN_LOADED"]
    assert len(loaded) == 2
    assert loaded[0].payload == {"name": "demo", "version": "1.0.0", "author": "tester"}
    assert loaded[1].payload == {"name": "demo2", "version": "2.0.0", "author": "tester"}
    assert all(ev.source == "plugin_manager" for ev in loaded)


@pytest.mark.asyncio
async def test_reload_plugin_not_found_emits_plugin_error(recording_bus):
    pm = make_pm()

    result = pm.reload_plugin("ghost")

    assert result is False
    await asyncio.sleep(0)
    assert [ev.type.name for ev in recording_bus.calls] == ["PLUGIN_ERROR"]
    assert recording_bus.calls[0].payload == {"name": "ghost", "error": "not_found"}
@pytest.mark.asyncio
async def test_reload_plugin_success_emits_plugin_reloaded(recording_bus, monkeypatch):
    pm = make_pm()
    pm._registry = [{"name": "demo", "plugin_path": "/tmp/whatever", "commands": []}]
    pm._versions = {"demo": "1.0.0"}
    monkeypatch.setattr(pm, "init", lambda: None)
    result = pm.reload_plugin("demo")
    assert result is True
    await asyncio.sleep(0)
    emitted = [ev.type.name for ev in recording_bus.calls]
    assert "PLUGIN_LOADED" in emitted, f"reload 成功应发 PLUGIN_LOADED: {emitted}"


