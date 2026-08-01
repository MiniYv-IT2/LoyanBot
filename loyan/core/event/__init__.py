"""LoyanBot 事件体系 — 消息事件路由 + 业务事件全广播

三层事件模型：消息事件 LoyanEvent（精准路由到 Runtime）、
业务事件 BusinessEvent（按 biz:{type} 全广播）、生命周期 LifecycleEvent（顺序执行）。
本包承载前两者的总线与类型定义。

用法:
    from loyan.core.event import event_bus, EventType, BusinessEvent, validate_payload

    await event_bus.publish(loyan_event)                       # 消息事件
    await event_bus.publish_business(biz_event)                # 业务事件
"""

from loyan.core.event.bus import EventBus
from loyan.core.event.types import BusinessEvent, EventType
from loyan.core.loyan_adapter.event import LoyanEvent

event_bus = EventBus()

__all__ = [
    "EventBus",
    "BusinessEvent",
    "EventType",
    "LoyanEvent",
    "event_bus",
]
