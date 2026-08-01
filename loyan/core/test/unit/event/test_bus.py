"""EventBus 单元测试 — 消息事件路由回归 + 业务事件增强

- subscribe/unsubscribe/优先级排序
- publish_business 广播到多个订阅者
- 通配订阅 biz:* 收到所有类型
- 错误隔离、超时保护、cancel 拦截
- biz_stats 计数、recent_events 环形缓冲
- 现有消息事件 publish 行为不变（回归）
"""

import asyncio

import pytest

from loyan.core.event import BusinessEvent, EventType, event_bus
from loyan.core.event.bus import EventBus
from loyan.core.event.types import GroupMemberJoinedPayload, validate_payload
from loyan.core.loyan_adapter.event import LoyanEvent


def _joined_event(source: str = "", tag: str = "") -> BusinessEvent:
    return BusinessEvent(
        type=EventType.GROUP_MEMBER_JOINED,
        payload=validate_payload(
            EventType.GROUP_MEMBER_JOINED, {"group_id": "100", "user_id": "200"}
        ),
        source=source,
        adapter_tag=tag,
    )


class TestSubscribeManagement:
    def test_subscribe_unsubscribe(self):
        bus = EventBus()
        handler = lambda ev: None
        bus.subscribe("biz:group_member_joined", handler)
        assert handler in bus._subscribers["biz:group_member_joined"]
        bus.unsubscribe("biz:group_member_joined", handler)
        assert handler not in bus._subscribers["biz:group_member_joined"]

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        bus = EventBus()
        order = []

        async def low(ev):
            order.append("low")

        async def high(ev):
            order.append("high")

        bus.subscribe("biz:*", low, priority=0)
        bus.subscribe("biz:*", high, priority=100)
        await bus.publish_business(_joined_event())
        assert order == ["high", "low"]


class TestPublishBusiness:
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(self):
        bus = EventBus()
        received = []

        async def h1(ev):
            received.append(ev.payload.group_id)

        async def h2(ev):
            received.append(ev.payload.user_id)

        bus.subscribe("biz:group_member_joined", h1)
        bus.subscribe("biz:group_member_joined", h2)
        await bus.publish_business(_joined_event())
        assert received == ["100", "200"]

    @pytest.mark.asyncio
    async def test_exact_type_only(self):
        # 订阅 A 类型不收 B 类型
        bus = EventBus()
        received = []

        async def h(ev):
            received.append(ev.type.value)

        bus.subscribe("biz:group_member_joined", h)
        await bus.publish_business(_joined_event())
        assert received == ["group_member_joined"]
        await bus.publish_business(
            BusinessEvent(
                EventType.GROUP_MEMBER_LEFT,
                validate_payload(EventType.GROUP_MEMBER_LEFT, {"group_id": "100", "user_id": "200"}),
            )
        )
        assert received == ["group_member_joined"]

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_types(self):
        bus = EventBus()
        received = []

        async def wildcard(ev):
            received.append(ev.type.value)

        bus.subscribe("biz:*", wildcard)
        await bus.publish_business(_joined_event())
        await bus.publish_business(
            BusinessEvent(
                EventType.FRIEND_ADDED,
                validate_payload(EventType.FRIEND_ADDED, {"user_id": "300"}),
            )
        )
        assert set(received) == {"group_member_joined", "friend_added"}


class TestIsolationAndControl:
    @pytest.mark.asyncio
    async def test_error_isolation(self):
        # 一个订阅者抛异常，其他订阅者仍收到
        bus = EventBus()
        received = []

        async def boom(ev):
            raise RuntimeError("boom")

        async def ok(ev):
            received.append("ok")

        bus.subscribe("biz:group_member_joined", boom)
        bus.subscribe("biz:group_member_joined", ok)
        await bus.publish_business(_joined_event())
        assert received == ["ok"]

    @pytest.mark.asyncio
    async def test_timeout_protection(self):
        # 慢订阅者被 wait_for 截断，publish 不被拖死
        bus = EventBus()
        bus._biz_timeout = 0.1
        finished = []

        async def slow(ev):
            await asyncio.sleep(1.0)
            finished.append("slow")

        bus.subscribe("biz:group_member_joined", slow)
        start = asyncio.get_event_loop().time()
        await bus.publish_business(_joined_event())
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.5
        assert finished == []

    @pytest.mark.asyncio
    async def test_cancel_stops_later_subscribers(self):
        # 订阅者 cancel 后后续订阅者不再收到
        bus = EventBus()
        received = []

        async def blocker(ev):
            ev.cancel()

        async def later(ev):
            received.append("later")

        bus.subscribe("biz:group_member_joined", blocker)
        bus.subscribe("biz:group_member_joined", later)
        bus.subscribe("biz:*", later)
        await bus.publish_business(_joined_event())
        assert received == []


class TestStatsAndBuffer:
    @pytest.mark.asyncio
    async def test_biz_stats_counting(self):
        bus = EventBus()
        await bus.publish_business(_joined_event())
        await bus.publish_business(_joined_event())
        await bus.publish_business(
            BusinessEvent(
                EventType.FRIEND_ADDED,
                validate_payload(EventType.FRIEND_ADDED, {"user_id": "300"}),
            )
        )
        stats = bus.biz_stats()
        assert stats["group_member_joined"] == 2
        assert stats["friend_added"] == 1
        # 无订阅者仍计数
        assert bus.biz_stats()["group_member_joined"] == 2

    @pytest.mark.asyncio
    async def test_recent_events_ring_buffer(self):
        bus = EventBus()
        for i in range(505):
            await bus.publish_business(
                BusinessEvent(
                    EventType.GROUP_MEMBER_JOINED,
                    GroupMemberJoinedPayload(group_id=str(i), user_id="u"),
                )
            )
        recent = bus.recent_events()
        assert len(recent) == 500
        # 环形缓冲：最旧的被丢弃，保留最新的（旧→新顺序）
        assert recent[0]["payload"]["group_id"] == "5"
        assert recent[-1]["payload"]["group_id"] == "504"
        # 每条含 type/source/timestamp/payload
        first = recent[0]
        assert first["type"] == "group_member_joined"
        assert first["source"] == ""
        assert first["timestamp"] > 0


class TestMessageEventRegression:
    @pytest.mark.asyncio
    async def test_publish_message_event_subscribers(self):
        # 现有消息事件 publish：订阅者仍被通知（回归）
        received = []

        async def h(ev):
            received.append(ev.sender_id)

        event_bus.subscribe("private", h)
        try:
            ev = LoyanEvent(sender_id="1", target_id="2", chat_type="private")
            await event_bus.publish(ev)
            await asyncio.sleep(0.05)
            assert received == ["1"]
        finally:
            event_bus.unsubscribe("private", h)
