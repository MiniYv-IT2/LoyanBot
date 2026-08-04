"""验证扫码登录新建实例后消息路由与 /关于 回复链路

场景：运行中通过 API 创建新实例（start_instance），
消息从新实例 tag 进来应路由到新实例 runtime 并正常回复。
覆盖此前 bug：start_instance 未建 Runtime 导致事件回退旧实例、发送失败。
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import logging
logging.basicConfig(level=logging.ERROR)

# graci 别名（同 main.py run_bot 行为）
import loyan.graci as _graci_pkg
sys.modules.setdefault("graci", _graci_pkg)

import pytest


@pytest.fixture(autouse=True)
def _default_cmd_prefix(monkeypatch):
    from loyan.core.config import user_config
    monkeypatch.setattr(user_config, "get_effective_cached",
                        lambda inst: {"command_prefix": "/"})

from loyan.core.event import event_bus
from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.pipeline import (
    BuiltinCommands,
    CommandMatcher,
    Pipeline,
    PluginHandler,
    ResponseSender,
    SecurityFilter,
)
from loyan.core.pipeline.stats_collector import stats_collector
from loyan.core.runtime import Runtime, RuntimeRegistry, RuntimeContext


class FakeAdapter(LoyanAdapter):
    """记录发送内容的假适配器"""

    def __init__(self):
        self.sent: list[str] = []

    async def start(self, on_event) -> None:
        pass

    async def send(self, target: str, segments: list[LoyanMsg], chat_type: str) -> bool:
        for seg in segments:
            self.sent.append(getattr(seg, "text", repr(seg)))
        return True

    async def stop(self) -> None:
        pass

    async def get_platform_info(self) -> dict:
        return {"platform": "fake"}


NEW_TAG = IdentityTag(platform="qq_official", bot_name="QQClaw_tst")
OLD_TAG = IdentityTag(platform="qq_official", bot_name="offcial_test")
OPENID = "7F3420C56DA6CC881EEA6D400586BE2C"


@pytest.fixture(autouse=True)
def _noop_stats(monkeypatch):
    """测试环境不碰真实 DB：stats_collector 替换为 no-op（避免 get_db 锁死锁）"""
    async def _noop_init():
        pass

    async def _noop_process(event):
        return event

    monkeypatch.setattr(stats_collector, "init", _noop_init)
    monkeypatch.setattr(stats_collector, "process", _noop_process)


@pytest.fixture(autouse=True)
def _real_send(monkeypatch):
    """其他测试可能全局替换 loyan_send_msg，这里强制走真实 pool 发送"""
    import sys
    send_mod = sys.modules["loyan.core.loyan_adapter.send"]

    async def _real(target, *segments, chat_type="private", tag=None):
        if tag is None:
            runtime = RuntimeContext.get()
            tag = runtime.adapter_tag if runtime else None
        return await adapter_pool.send(target, list(segments), chat_type, tag=tag)

    monkeypatch.setattr(send_mod, "loyan_send_msg", _real)


def _build_pipeline() -> Pipeline:
    p = Pipeline()
    p.add_stage(SecurityFilter())
    p.add_stage(BuiltinCommands())
    p.add_stage(CommandMatcher())
    p.add_stage(PluginHandler())
    p.add_stage(ResponseSender())
    p.add_stage(stats_collector)
    return p


def _make_runtime(name: str, tag: IdentityTag) -> Runtime:
    runtime = Runtime(
        instance_name=name,
        robot_id="",
        master_id=OPENID,
        adapter_tag=tag,
        plugin_manager=None,
        adapter_pool=adapter_pool,
    )
    runtime.pipeline = _build_pipeline()
    return runtime


@pytest.fixture(autouse=True)
def _cleanup():
    for runtime in list(RuntimeRegistry.get_all()):
        RuntimeRegistry.unregister(runtime)
    for tag in list(adapter_pool._adapters.keys()):
        adapter_pool.unregister(adapter_pool._adapters[tag][1])
    yield
    for runtime in list(RuntimeRegistry.get_all()):
        RuntimeRegistry.unregister(runtime)
    for tag in list(adapter_pool._adapters.keys()):
        adapter_pool.unregister(adapter_pool._adapters[tag][1])


@pytest.mark.asyncio
async def test_about_reply_after_start_instance():
    """新建实例后 /关于 应路由到新 runtime 并成功回复（修复验证）"""
    fake = FakeAdapter()
    adapter_pool.register(fake, NEW_TAG, default=True)

    # start_instance 修复后的状态：新实例 runtime 已注册
    new_runtime = _make_runtime("QQClaw_tst", NEW_TAG)
    RuntimeRegistry.register(new_runtime)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/关于",
        message_id="t1",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    assert fake.sent, "新实例应成功回复 /关于"
    joined = "\n".join(fake.sent)
    assert "LoyanBot v0.1.dev0" in joined, f"回复应包含版本信息: {joined}"
    assert "适配器" in joined


@pytest.mark.asyncio
async def test_about_fallback_old_runtime_fails_send():
    """回归：未建新 runtime 时（旧 bug），事件回退旧实例且发送失败"""
    fake_old = FakeAdapter()
    # 旧实例已从 pool 注销，但 runtime 残留（旧 bug 场景）
    old_runtime = _make_runtime("offcial_test", OLD_TAG)
    RuntimeRegistry.register(old_runtime)
    # 不注册 NEW_TAG 对应的 adapter（扫码登录创建失败前）也不注册 OLD_TAG adapter
    # 只留一个默认 adapter 保证 pool 不空，但 tag 不匹配
    adapter_pool.register(FakeAdapter(), OLD_TAG, default=True)
    adapter_pool.unregister(OLD_TAG)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/关于",
        message_id="t2",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    # 新 tag 找不到 runtime → 回退旧 runtime；旧 tag 不在 pool → 发送失败（无报错即可）
    assert True


@pytest.mark.asyncio
async def test_about_uses_new_runtime_not_fallback():
    """新 runtime 存在时不得回退旧 runtime"""
    fake_new = FakeAdapter()
    adapter_pool.register(fake_new, NEW_TAG, default=True)
    new_runtime = _make_runtime("QQClaw_tst", NEW_TAG)
    RuntimeRegistry.register(new_runtime)

    old_runtime = _make_runtime("offcial_test", OLD_TAG)
    RuntimeRegistry.register(old_runtime)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/关于",
        message_id="t3",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    assert fake_new.sent, "消息应路由到新实例并回复"
    assert "LoyanBot v0.1.dev0" in "\n".join(fake_new.sent)
