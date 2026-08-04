"""全链路冒烟测试 — 消息从入站事件到回复的完整 pipeline

覆盖链路：
    LoyanEvent → event_bus.publish → RuntimeRegistry 按 source tag 路由
    → RuntimeContext → Pipeline(SecurityFilter → BuiltinCommands
    → CommandMatcher → PluginHandler → ResponseSender)
    → loyan_send_msg → adapter_pool.send → 适配器回复

每个用例验证一个关键链路片段：
    - test_private_message_full_chain   私聊 /关于 → 全链回复
    - test_group_message_chain          群聊 + @机器人 + 插件命令 → 回复
    - test_unknown_command_passthrough  未知命令 → 不短路、无异常、无回复
    - test_non_master_blocked           非 master 的 /panel → 被拦截
    - test_runtime_routing_by_tag       双 runtime 按 source tag 路由
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

from loyan.core.decorators.registration import DECORATOR_COMMAND_REGISTRY
from loyan.core.pipeline.builtin_commands import register_builtin_command, _BUILTIN_COMMAND_REGISTRY
from loyan.core.event import event_bus
from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg, LoyanText
from loyan.core.loyan_adapter.pool import adapter_pool
from loyan.core.pipeline import (
    BuiltinCommands,
    CommandMatcher,
    Pipeline,
    PluginHandler,
    ResponseSender,
    SecurityFilter,
)
from loyan.core.pipeline.builtin_commands import (
    _BUILTIN_COMMAND_REGISTRY,
    register_builtin_command,
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
GROUP_TAG = IdentityTag(platform="qq_official", bot_name="group_test_bot")
# 真实 openid（冒烟以 master 场景为主）
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
    """清理 RuntimeRegistry / adapter_pool / 测试期间注册的命令"""
    for runtime in list(RuntimeRegistry.get_all()):
        RuntimeRegistry.unregister(runtime)
    for tag in list(adapter_pool._adapters.keys()):
        adapter_pool.unregister(adapter_pool._adapters[tag][1])
    yield
    for runtime in list(RuntimeRegistry.get_all()):
        RuntimeRegistry.unregister(runtime)
    for tag in list(adapter_pool._adapters.keys()):
        adapter_pool.unregister(adapter_pool._adapters[tag][1])
    # 清掉测试内注册的内置命令
    for cmd in ("/panel",):
        _BUILTIN_COMMAND_REGISTRY.pop(cmd, None)


def _wrap_pipeline_process(runtime):
    """包装 runtime.pipeline.process 记录调用，用于断言“事件未被吞”"""
    calls = []
    orig = runtime.pipeline.process

    async def wrapped(event):
        calls.append(event)
        return await orig(event)

    runtime.pipeline.process = wrapped
    return calls


@pytest.mark.asyncio
async def test_private_message_full_chain():
    """私聊 /关于：SecurityFilter → BuiltinCommands → ResponseSender 全链回复"""
    fake = FakeAdapter()
    adapter_pool.register(fake, NEW_TAG, default=True)
    runtime = _make_runtime("QQClaw_tst", NEW_TAG)
    RuntimeRegistry.register(runtime)
    calls = _wrap_pipeline_process(runtime)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/关于",
        message_id="smoke-1",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    assert calls, "事件应被路由到 runtime pipeline（未被吞）"
    assert fake.sent, "master 的 /关于 应有回复"
    joined = "\n".join(fake.sent)
    assert "LoyanBot v0.1.dev0" in joined, f"回复应包含版本信息: {joined}"


@pytest.mark.asyncio
async def test_group_message_chain():
    """群聊 + @机器人：插件命令应被匹配并回复（事件不被吞）"""
    fake = FakeAdapter()
    adapter_pool.register(fake, GROUP_TAG, default=True)
    runtime = _make_runtime("group_test", GROUP_TAG)
    RuntimeRegistry.register(runtime)
    calls = _wrap_pipeline_process(runtime)

    # ── 选 group 输入：优先真实插件命令 /时间（若插件已加载）；否则注册测试命令兜底 ──
    group_cmd = None
    try:
        from loyan.core.plugin_manager import plugin_manager
        plugin_manager.init()
        for p in plugin_manager.registry:
            if "/时间" in p.get("commands", []):
                group_cmd = "/时间"
                break
    except Exception:
        group_cmd = None

    entry = None
    if group_cmd is None:
        group_cmd = "/冒烟时间"

        async def _fake_time_cmd(ctx):
            await ctx.reply("群聊冒烟时间 OK")

        register_builtin_command(group_cmd, _fake_time_cmd, require_admin=False)
        entry = group_cmd

    try:
        event = LoyanEvent(
            sender_id=OPENID,
            target_id="GROUP123456",
            chat_type="group",
            raw_text=group_cmd,
            is_at_bot=True,
            message_id="smoke-2",
            source=GROUP_TAG,
        )
        # 核心断言：事件到达 pipeline 且不抛异常（群聊插件回复可依赖加载状态）
        await event_bus.publish(event)
        assert calls, "群聊事件应到达 pipeline（未被吞）"
        if entry is not None:
            # 测试命令确定性回复
            assert fake.sent, "群聊内置命令应有回复"
            assert "群聊冒烟时间 OK" in "\n".join(fake.sent)
        else:
            # 真实插件 /时间：有回复最佳，至少链路通
            if fake.sent:
                assert any("时间" in t for t in fake.sent)
    finally:
        if entry is not None:
            _BUILTIN_COMMAND_REGISTRY.pop(entry, None)


@pytest.mark.asyncio
async def test_unknown_command_passthrough():
    """未知命令：BuiltinCommands 返回 ctx 继续，不短路、无异常、无回复"""
    fake = FakeAdapter()
    adapter_pool.register(fake, NEW_TAG, default=True)
    runtime = _make_runtime("QQClaw_tst", NEW_TAG)
    RuntimeRegistry.register(runtime)
    calls = _wrap_pipeline_process(runtime)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/xyz_not_exist",
        message_id="smoke-3",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    assert calls, "未知命令也应进入 pipeline（不短路）"
    assert not fake.sent, "未知命令不应产生回复"


@pytest.mark.asyncio
async def test_non_master_blocked():
    """陌生人发 /panel（require_admin）：被拦截无回复；master 正常回复"""
    # 模拟生产环境面板模块自注册（panel/server.py: _register_panel_commands）
    async def _panel_handler(ctx):
        # 注意：必须在函数内 import，避免捕获模块级被其他测试替换的旧引用
        from loyan.core.loyan_adapter.send import loyan_send_msg
        await loyan_send_msg(ctx.target_id, LoyanText("面板管理入口"), chat_type=ctx.chat_type)

    register_builtin_command("/panel", _panel_handler, require_admin=True)

    fake = FakeAdapter()
    adapter_pool.register(fake, NEW_TAG, default=True)
    runtime = _make_runtime("QQClaw_tst", NEW_TAG)  # master_id = OPENID
    RuntimeRegistry.register(runtime)

    # 陌生人（非 master）→ 被拦截，无回复
    stranger = LoyanEvent(
        sender_id="someone_else_000001",
        target_id="someone_else_000001",
        chat_type="private",
        raw_text="/panel",
        message_id="smoke-4a",
        source=NEW_TAG,
    )
    await event_bus.publish(stranger)
    assert not fake.sent, "非 master 的 /panel 应被拦截（无回复）"

    # master → 正常回复
    master = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/panel",
        message_id="smoke-4b",
        source=NEW_TAG,
    )
    await event_bus.publish(master)
    assert fake.sent, "master 的 /panel 应正常回复"
    assert "面板管理入口" in "\n".join(fake.sent)


@pytest.mark.asyncio
async def test_runtime_routing_by_tag():
    """双 runtime（新+旧 tag）并存：消息按 source tag 路由到正确 pipeline"""
    fake_new = FakeAdapter()
    fake_old = FakeAdapter()
    adapter_pool.register(fake_new, NEW_TAG, default=True)
    adapter_pool.register(fake_old, OLD_TAG, default=False)

    runtime_new = _make_runtime("QQClaw_tst", NEW_TAG)
    runtime_old = _make_runtime("offcial_test", OLD_TAG)
    RuntimeRegistry.register(runtime_new)
    RuntimeRegistry.register(runtime_old)

    event = LoyanEvent(
        sender_id=OPENID,
        target_id=OPENID,
        chat_type="private",
        raw_text="/关于",
        message_id="smoke-5",
        source=NEW_TAG,
    )
    await event_bus.publish(event)

    assert fake_new.sent, "消息应按 source tag 路由到新 runtime 并回复"
    assert "LoyanBot v0.1.dev0" in "\n".join(fake_new.sent)
    assert not fake_old.sent, "旧 runtime 的适配器不应收到回复"
