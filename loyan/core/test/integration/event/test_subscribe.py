"""集成测试 — graci on_event 插件订阅业务事件全链路

覆盖:
    - on_event 字符串/EventType 枚举注册 → publish_business → 订阅者收到 BusinessEvent
    - 通配订阅 biz:* 收到所有业务事件
    - unsubscribe 后不再收到
    - 多订阅者并行 + 错误隔离（一个抛异常其他照收）
    - cancel() 拦截（第一个订阅者 cancel，后续不再收到）
    - 全局 event_bus + 测试后清理（防污染其他测试）

插件用法示例:
    @on_event("group_member_joined")
    async def on_join(ev: BusinessEvent):
        await loyan_send_msg(ev.payload["group_id"], LoyanText("欢迎新朋友！"), chat_type="group")
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

# graci 别名（同 main.py run_bot 行为），验证顶层导出
import loyan.graci as _graci_pkg
sys.modules.setdefault("graci", _graci_pkg)
from graci import on_event

# 事件核心（bus.py/types.py）由另一智能体实施，未就绪时跳过
try:
    from loyan.core.event import event_bus, EventType, BusinessEvent
except Exception:
    event_bus = None
    EventType = None
    BusinessEvent = None

pytestmark = pytest.mark.skipif(
    event_bus is None or not hasattr(event_bus, "publish_business"),
    reason="事件核心（bus.py/types.py）未就绪",
)

# ── 全局订阅登记（防污染其他测试）──

_REGISTERED: list = []


def _subscribe(key, handler, priority=0):
    """订阅并登记，供 autouse fixture 测试后统一 unsubscribe"""
    event_bus.subscribe(key, handler, priority=priority)
    _REGISTERED.append((key, handler))


@pytest.fixture(autouse=True)
def _cleanup_subscriptions():
    """清理：unsubscribe 本模块登记的所有订阅（全局 event_bus）"""
    yield
    for key, handler in _REGISTERED:
        try:
            event_bus.unsubscribe(key, handler)
        except Exception:
            pass
    _REGISTERED.clear()


def _make_event(event_type=None, **payload):
    """构造 BusinessEvent（默认群成员加入事件）"""
    if event_type is None:
        event_type = EventType.GROUP_MEMBER_JOINED
    if not payload:
        payload = {"group_id": "g1", "user_id": "u1"}
    return BusinessEvent(type=event_type, payload=payload, source="integration_test")


async def _settle():
    """防御性等待，兼容 fire-and-forget 派发实现"""
    await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_on_event_str_subscribe_receives():
    """字符串注册：@on_event("group_member_joined") → publish_business 收到"""
    received = []

    @on_event("group_member_joined")
    async def on_join(ev):
        received.append(ev)

    _REGISTERED.append(("biz:group_member_joined", on_join))
    await event_bus.publish_business(_make_event())
    await _settle()

    assert len(received) == 1
    ev = received[0]
    assert ev.type == EventType.GROUP_MEMBER_JOINED
    assert ev.payload["group_id"] == "g1"
    assert ev.source == "integration_test"


@pytest.mark.asyncio
async def test_on_event_enum_subscribe_receives():
    """枚举注册：@on_event(EventType.GROUP_MEMBER_JOINED) 与字符串等效"""
    received = []

    @on_event(EventType.GROUP_MEMBER_JOINED)
    async def on_join(ev):
        received.append(ev)

    _REGISTERED.append(("biz:group_member_joined", on_join))
    await event_bus.publish_business(_make_event())
    await _settle()

    assert len(received) == 1
    assert received[0].type == EventType.GROUP_MEMBER_JOINED


@pytest.mark.asyncio
async def test_wildcard_receives_all_events():
    """通配 @on_event("*")：biz:* 收到所有业务事件"""
    got = []

    @on_event("*")
    async def watcher(ev):
        got.append(ev.type)

    _REGISTERED.append(("biz:*", watcher))
    await event_bus.publish_business(_make_event(EventType.GROUP_MEMBER_JOINED))
    await event_bus.publish_business(
        _make_event(EventType.PLATFORM_CONNECTED, platform="onebot", tag="t1")
    )
    await _settle()

    assert len(got) == 2
    assert EventType.GROUP_MEMBER_JOINED in got
    assert EventType.PLATFORM_CONNECTED in got


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    """unsubscribe 后不再收到"""
    got = []

    async def handler(ev):
        got.append(ev)

    _subscribe("biz:group_member_joined", handler)
    await event_bus.publish_business(_make_event())
    await _settle()
    assert len(got) == 1

    event_bus.unsubscribe("biz:group_member_joined", handler)
    _REGISTERED.remove(("biz:group_member_joined", handler))
    await event_bus.publish_business(_make_event())
    await _settle()
    assert len(got) == 1


@pytest.mark.asyncio
async def test_error_isolation_other_subscribers_still_get():
    """一个订阅者抛异常，不影响其他订阅者收到"""
    got = []

    async def boom(ev):
        raise RuntimeError("订阅者异常")

    async def normal(ev):
        got.append(ev)

    _subscribe("biz:group_member_joined", boom, priority=10)
    _subscribe("biz:group_member_joined", normal)
    await event_bus.publish_business(_make_event())
    await _settle()

    assert len(got) == 1


@pytest.mark.asyncio
async def test_cancel_intercepts_later_subscribers():
    """第一个订阅者 cancel()，后续订阅者不再收到"""
    got = []

    async def canceller(ev):
        ev.cancel()

    async def later(ev):
        got.append(ev)

    _subscribe("biz:group_member_joined", canceller, priority=10)
    _subscribe("biz:group_member_joined", later)
    await event_bus.publish_business(_make_event())
    await _settle()

    assert got == []
