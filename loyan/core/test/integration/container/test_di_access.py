"""调用方 DI 访问集成测试 — send.py / http_routes.py 通过全局容器注入可替换依赖

覆盖：
    - 正常环境（默认容器）下 loyan_send_msg 仍可调用，不抛异常
    - set_container() 注入 FakePool 后，loyan_send_msg / loyan_call_api 走注入路径
    - http_routes._get_event_bus() 注入路径与默认回落路径
"""

import importlib
import pytest

from loyan.core.container import Container, get_container, set_container


@pytest.fixture(autouse=True)
def _real_send_impl():
    """legacy 脚本 test_plugin_commands.py 在 import 时全局替换了
    send.loyan_send_msg，这里 reload 恢复真实实现，保证本文件测的是真函数"""
    importlib.reload(importlib.import_module("loyan.core.loyan_adapter.send"))
    yield


class FakeAdapter:
    """记录 call_api 调用的假适配器"""

    def __init__(self):
        self.api_calls = []

    async def call_api(self, action, params=None):
        self.api_calls.append((action, params))
        return {"echo": action}


class FakePool:
    """记录 send / get 调用的假 AdapterPool"""

    def __init__(self):
        self.sent = []
        self.got_default = 0
        self.got_tag = 0
        self.default_adapter = FakeAdapter()

    async def send(self, target, segments, chat_type, tag=None):
        self.sent.append((target, segments, chat_type, tag))
        return True

    def get(self, tag):
        self.got_tag += 1
        return self.default_adapter

    def get_default(self):
        self.got_default += 1
        return self.default_adapter


@pytest.fixture
def injected_container():
    """把全局默认容器替换为注入 FakePool / FakeEventBus 的容器，用毕复位"""
    old = get_container()
    container = Container()
    container.register("adapter_pool", lambda _c: FakePool())
    container.register("event_bus", lambda _c: object())
    set_container(container)
    try:
        yield container
    finally:
        set_container(old)


# ── send.py ──

@pytest.mark.asyncio
async def test_loyan_send_msg_normal_env_no_crash():
    """正常环境（默认容器，无适配器）调用 loyan_send_msg 不抛异常"""
    from loyan.core.loyan_adapter.message import LoyanText
    from loyan.core.loyan_adapter.send import loyan_send_msg

    ok = await loyan_send_msg("123", LoyanText(text="hi"), chat_type="private")
    assert isinstance(ok, bool)


@pytest.mark.asyncio
async def test_loyan_send_msg_uses_injected_pool(injected_container):
    """注入 FakePool 后 loyan_send_msg 走注入路径（FakePool.send 被调用）"""
    from loyan.core.loyan_adapter.message import LoyanText
    from loyan.core.loyan_adapter.send import loyan_send_msg

    pool = injected_container.get("adapter_pool")
    ok = await loyan_send_msg("123", LoyanText(text="hi"), chat_type="private")
    assert ok is True
    assert len(pool.sent) == 1
    assert pool.sent[0][0] == "123"
    assert pool.sent[0][2] == "private"


@pytest.mark.asyncio
async def test_loyan_call_api_uses_injected_pool(injected_container):
    """注入 FakePool 后 loyan_call_api 走注入路径（FakeAdapter.call_api 被调用）"""
    from loyan.core.loyan_adapter.send import loyan_call_api

    pool = injected_container.get("adapter_pool")
    result = await loyan_call_api("get_friend_list", {"x": 1})
    assert result == {"echo": "get_friend_list"}
    assert pool.got_default == 1
    assert pool.default_adapter.api_calls == [("get_friend_list", {"x": 1})]


# ── http_routes.py ──

def test_http_routes_event_bus_default():
    """默认回落：_get_event_bus() 返回模块级 event_bus 单例"""
    from loyan.core.event import event_bus
    from loyan.core.loyan_adapter.platform.onebot import http_routes

    assert http_routes._get_event_bus() is event_bus


def test_http_routes_event_bus_injectable(injected_container):
    """注入后 _get_event_bus() 返回容器中的 Fake 实例"""
    from loyan.core.loyan_adapter.platform.onebot import http_routes

    bus = injected_container.get("event_bus")
    assert http_routes._get_event_bus() is bus
