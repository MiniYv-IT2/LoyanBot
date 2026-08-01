"""InstanceManager 单元测试 — 锁 / 回滚 / 状态机 / 注入 / API 转发

用 FakePool / FakeRegistry / FakeAdapter 注入构造，不碰全局单例。
覆盖：
- reload 成功路径（旧 stop 新 start、tag 更新、default 保留）
- reload 失败回滚（新 adapter start 抛错 → 旧 adapter 重新注册，pool 里仍有旧 tag）
- 并发 reload 同一实例串行化（锁保证不交错，用计数器验证）
- start 无 runtime 时建 runtime
- stop 后状态 stopped
- API 转发函数（模块级 reload_instance 等）仍可调用且走 _instance
"""

import asyncio
import json
import logging
import os
from types import SimpleNamespace

import pytest

from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.runtime import manager as manager_mod


# ══════════════════════════════════════════════════════════
# Fakes（简单类，记录调用）
# ══════════════════════════════════════════════════════════


class FakeAdapter:
    """假适配器：start/stop 记录次数，可配置 start 抛错"""

    def __init__(self, name="fake", fail_start=False, counter=None):
        self.name = name
        self.fail_start = fail_start
        self.counter = counter  # dict: {"active": int, "max": int} 可选
        self.started = 0
        self.stopped = 0
        self.tag = None

    async def start(self, on_event=None):
        if self.counter is not None:
            self.counter["active"] += 1
            self.counter["max"] = max(self.counter["max"], self.counter["active"])
            await asyncio.sleep(0.02)
            self.counter["active"] -= 1
        if self.fail_start:
            raise RuntimeError("fake start boom")
        self.started += 1

    async def stop(self):
        if self.counter is not None:
            self.counter["active"] += 1
            self.counter["max"] = max(self.counter["max"], self.counter["active"])
            await asyncio.sleep(0.02)
            self.counter["active"] -= 1
        self.stopped += 1

    async def send(self, *args, **kwargs):
        return True


class FakePool:
    """假适配器池：镜像 AdapterPool 公共 API，记录 register/unregister/send"""

    def __init__(self):
        self._adapters = {}   # key -> (adapter, tag)
        self._default_key = None
        self.calls = []       # ("register", tag, default) / ("unregister", tag)

    def register(self, adapter, tag, default=False):
        key = tag.identity_key
        self._adapters[key] = (adapter, tag)
        if self._default_key is None or default:
            self._default_key = key
        self.calls.append(("register", tag, default))

    def unregister(self, tag):
        key = tag.identity_key
        if key in self._adapters:
            del self._adapters[key]
        if self._default_key == key:
            self._default_key = next(iter(self._adapters)) if self._adapters else None
        self.calls.append(("unregister", tag))

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

    async def send(self, *args, **kwargs):
        return True


class FakeRegistry:
    """假 Runtime 注册表：记录 register/unregister"""

    def __init__(self):
        self._runtimes = []
        self._by_robot_id = {}
        self.calls = []

    def register(self, runtime):
        self.calls.append(("register", getattr(runtime, "instance_name", "?")))
        self._runtimes.append(runtime)
        if getattr(runtime, "robot_id", ""):
            self._by_robot_id[runtime.robot_id] = runtime

    def unregister(self, runtime):
        self.calls.append(("unregister", getattr(runtime, "instance_name", "?")))
        if runtime in self._runtimes:
            self._runtimes.remove(runtime)
        if getattr(runtime, "robot_id", ""):
            self._by_robot_id.pop(runtime.robot_id, None)

    def get_all(self):
        return list(self._runtimes)

    def get_by_robot_id(self, robot_id):
        return self._by_robot_id.get(robot_id)


class FakeRuntime:
    """假 Runtime：仅需 instance_name / robot_id / adapter_tag"""

    def __init__(self, name, robot_id="", adapter_tag=None):
        self.instance_name = name
        self.robot_id = robot_id
        self.adapter_tag = adapter_tag


class FakeEventBus:
    def __init__(self):
        self.published = []

    async def publish(self, event):
        self.published.append(event)

    async def publish_business(self, event):
        self.published.append(event)


# ══════════════════════════════════════════════════════════
# fixtures
# ══════════════════════════════════════════════════════════


def _write_config(instances_dir: str, name: str, **overrides) -> str:
    cfg = {
        "enabled": True,
        "platform": "fake",
        "bot_name": name,
        "robot_id": f"rid_{name}",
        "master_id": "m1",
        "admins_id": [],
    }
    cfg.update(overrides)
    d = os.path.join(instances_dir, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


@pytest.fixture
def instances_dir(tmp_path, monkeypatch):
    """把 manager.get_instances_dir 指向临时目录"""
    d = str(tmp_path / "instances")
    os.makedirs(d, exist_ok=True)
    monkeypatch.setattr(manager_mod, "get_instances_dir", lambda: d)
    return d


@pytest.fixture
def no_stats(monkeypatch):
    """init_instances 不碰真实 DB：stats_collector.init 替换为 no-op"""
    async def _noop():
        pass
    monkeypatch.setattr(manager_mod.stats_collector, "init", _noop)


def make_manager(pool=None, registry=None):
    pool = pool or FakePool()
    registry = registry or FakeRegistry()
    return manager_mod.InstanceManager(pool, registry, SimpleNamespace(), FakeEventBus())


@pytest.fixture
def patch_create(monkeypatch):
    """替换 _create_and_prepare_adapter，让测试可控返回假适配器"""
    def _patch(fn):
        monkeypatch.setattr(manager_mod, "_create_and_prepare_adapter", fn)
    return _patch


@pytest.fixture
def patch_build(monkeypatch):
    """替换 _build_runtime，避免真实 Pipeline / 日志副作用"""
    def _patch(fn):
        monkeypatch.setattr(manager_mod, "_build_runtime", fn)
    return _patch


# ══════════════════════════════════════════════════════════
# reload 成功路径
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reload_success(instances_dir, patch_create):
    _write_config(instances_dir, "bot1")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    old = FakeAdapter("old")
    old_tag = IdentityTag(platform="fake", bot_name="bot1")
    pool.register(old, old_tag, default=True)
    runtime = FakeRuntime("bot1", "rid_bot1", old_tag)
    registry.register(runtime)

    new = FakeAdapter("new")
    new_tag = IdentityTag(platform="fake", bot_name="bot1")

    async def _create(cfg, runtime=None):
        return new, new_tag

    patch_create(_create)

    result = await mgr.reload("bot1")

    assert result == {"success": True}
    # 旧 adapter 被 stop，新 adapter 被 start
    assert old.stopped == 1
    assert new.started == 1
    # pool 中旧 tag 移除、新 tag 注册（保留 default）
    assert pool.get(old_tag) is None
    assert pool.get(new_tag) is new
    assert pool.get_default_tag().identity_key == new_tag.identity_key
    # runtime tag 更新
    assert runtime.adapter_tag.identity_key == new_tag.identity_key
    assert mgr.state("bot1") == "running"


# ══════════════════════════════════════════════════════════
# reload 失败回滚
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reload_failure_rollback(instances_dir, patch_create):
    _write_config(instances_dir, "bot1")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    old = FakeAdapter("old")
    old_tag = IdentityTag(platform="fake", bot_name="bot1")
    pool.register(old, old_tag, default=True)
    runtime = FakeRuntime("bot1", "rid_bot1", old_tag)
    registry.register(runtime)

    new = FakeAdapter("new", fail_start=True)

    async def _create(cfg, runtime=None):
        return new, IdentityTag(platform="fake", bot_name="bot1")

    patch_create(_create)

    result = await mgr.reload("bot1")

    assert result["success"] is False
    assert "start_failed" in result["error"]
    # 回滚：旧 adapter 重新注册，pool 里仍有旧 tag
    assert pool.get(old_tag) is old
    assert old_tag in pool.all_tags
    # 旧 runtime tag 恢复
    assert runtime.adapter_tag.identity_key == old_tag.identity_key
    # 回滚成功后机器人不掉线 → running
    assert mgr.state("bot1") == "running"


# ══════════════════════════════════════════════════════════
# 并发 reload 串行化
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_concurrent_reload_serialized(instances_dir, patch_create):
    _write_config(instances_dir, "bot1")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    old = FakeAdapter("old")
    old_tag = IdentityTag(platform="fake", bot_name="bot1")
    pool.register(old, old_tag, default=True)

    counter = {"active": 0, "max": 0}
    made = []

    async def _create(cfg, runtime=None):
        adp = FakeAdapter(f"new-{len(made)}", counter=counter)
        tag = IdentityTag(platform="fake", bot_name="bot1")
        adp.tag = tag
        made.append((adp, tag))
        return adp, tag

    patch_create(_create)

    r1, r2 = await asyncio.gather(mgr.reload("bot1"), mgr.reload("bot1"))

    assert r1["success"] is True
    assert r2["success"] is True
    # 锁保证两次 reload 不交错：任意时刻最多 1 个 start/stop 在跑
    assert counter["max"] == 1
    # 两个新 adapter 都被 start，最后一个仍注册在 pool
    assert len(made) == 2
    assert made[0][0].started == 1 and made[0][0].stopped == 1
    assert made[1][0].started == 1
    assert pool.get(made[1][1]) is made[1][0]
    assert made[0][1] not in pool.all_tags


# ══════════════════════════════════════════════════════════
# start 无 runtime 时建 runtime
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_start_builds_runtime_when_missing(instances_dir, patch_create, patch_build):
    _write_config(instances_dir, "bot2")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    adapter = FakeAdapter("bot2")
    tag = IdentityTag(platform="fake", bot_name="bot2")

    def _build(cfg, plugin_manager=None, adapter_pool=None):
        return FakeRuntime(cfg["_dir_name"], cfg.get("robot_id", ""), None)

    async def _create(cfg, runtime=None):
        return adapter, tag

    patch_build(_build)
    patch_create(_create)

    result = await mgr.start("bot2")

    assert result == {"success": True}
    # 无 runtime → 自动构建并注册
    assert len(registry.get_all()) == 1
    assert registry.get_all()[0].instance_name == "bot2"
    assert pool.get(tag) is adapter
    assert mgr.state("bot2") == "running"


# ══════════════════════════════════════════════════════════
# stop 后状态 stopped
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_stop_sets_state_stopped(instances_dir):
    _write_config(instances_dir, "bot1")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    adapter = FakeAdapter("bot1")
    tag = IdentityTag(platform="fake", bot_name="bot1")
    pool.register(adapter, tag, default=True)
    runtime = FakeRuntime("bot1", "rid_bot1", tag)
    registry.register(runtime)

    result = await mgr.stop("bot1")

    assert result == {"success": True}
    assert adapter.stopped == 1
    assert pool.get(tag) is None
    assert registry.get_all() == []
    assert mgr.state("bot1") == "stopped"

    # 重复 stop → not_running，状态仍 stopped
    again = await mgr.stop("bot1")
    assert again == {"success": False, "error": "not_running"}
    assert mgr.state("bot1") == "stopped"


# ══════════════════════════════════════════════════════════
# init_instances 失败聚合
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_init_instances_aggregates_failures(instances_dir, no_stats, patch_create, patch_build, caplog):
    _write_config(instances_dir, "ok")
    _write_config(instances_dir, "bad")
    pool = FakePool()
    registry = FakeRegistry()
    mgr = make_manager(pool, registry)

    def _build(cfg, plugin_manager=None, adapter_pool=None):
        return FakeRuntime(cfg["_dir_name"], cfg.get("robot_id", ""), None)

    async def _create(cfg, runtime=None):
        if cfg["_dir_name"] == "bad":
            raise RuntimeError("kaboom")
        adp = FakeAdapter(cfg["_dir_name"])
        return adp, IdentityTag(platform="fake", bot_name=cfg["_dir_name"])

    patch_build(_build)
    patch_create(_create)

    with caplog.at_level(logging.ERROR, logger="Core.Instance"):
        loaded = await mgr.init_instances()

    assert loaded == 1
    assert mgr.state("ok") == "running"
    assert mgr.state("bad") == "error"
    assert "1/2 instances failed" in caplog.text
    assert "bad(RuntimeError: kaboom)" in caplog.text


# ══════════════════════════════════════════════════════════
# 模块级 API 转发
# ══════════════════════════════════════════════════════════


class _StubInstance:
    """替身 _instance：记录转发调用"""

    def __init__(self):
        self.calls = []

    async def reload(self, name):
        self.calls.append(("reload", name))
        return {"success": True}

    async def start(self, name):
        self.calls.append(("start", name))
        return {"success": True}

    async def stop(self, name):
        self.calls.append(("stop", name))
        return {"success": True}

    async def rename(self, old, new):
        self.calls.append(("rename", old, new))
        return {"success": True}

    async def init_instances(self):
        self.calls.append(("init_instances",))
        return 3


@pytest.mark.asyncio
async def test_module_level_api_forwards(monkeypatch):
    stub = _StubInstance()
    monkeypatch.setattr(manager_mod, "_instance", stub)

    assert await manager_mod.reload_instance("bot1") == {"success": True}
    assert await manager_mod.start_instance("bot2") == {"success": True}
    assert await manager_mod.stop_instance("bot1") == {"success": True}
    assert await manager_mod.rename_instance("bot1", "bot3") == {"success": True}
    assert await manager_mod.init_instances() == 3

    assert stub.calls == [
        ("reload", "bot1"),
        ("start", "bot2"),
        ("stop", "bot1"),
        ("rename", "bot1", "bot3"),
        ("init_instances",),
    ]


# ══════════════════════════════════════════════════════════
# state() / 默认状态
# ══════════════════════════════════════════════════════════


def test_state_defaults_to_stopped():
    mgr = make_manager()
    assert mgr.state("ghost") == "stopped"


def test_set_event_callback_propagation(monkeypatch):
    mgr = make_manager()
    seen = []

    def cb(e):
        seen.append(e)

    mgr.set_event_callback(cb)
    assert mgr._event_callback is cb

    # 模块级 set_event_callback 同步到 _instance
    monkeypatch.setattr(manager_mod, "_instance", mgr)
    manager_mod.set_event_callback(cb)
    assert manager_mod._on_event_callback is cb
    assert mgr._event_callback is cb
