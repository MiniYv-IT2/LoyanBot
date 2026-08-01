"""EventBus 核心实现 — 消息事件路由 + 业务事件全广播

两个派发通道：
    1. publish(LoyanEvent)      — 消息事件，按 source tag 精准路由到 Runtime Pipeline（旧逻辑，不改）
    2. publish_business(...)    — 业务事件，按 biz:{type} 全广播，支持 biz:* 通配、错误隔离、超时保护
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List

from loyan.core.event.types import BusinessEvent
from loyan.core.loyan_adapter.event import LoyanEvent

_logger = logging.getLogger("Core.Event")


class EventBus:
    """异步事件总线

    支持两种派发模式：
        1. subscribe() — 灵活的订阅机制，每个 event_type 可绑定多个处理器
        2. publish() → RuntimeRegistry → RuntimeContext → runtime.pipeline
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        # 业务事件增强（本轮新增）
        self._biz_timeout: float = 30.0          # 业务订阅者超时保护（秒）
        self._biz_stats: Dict[str, int] = {}     # 每个事件类型发布次数统计
        self._recent: Deque[dict] = deque(maxlen=500)  # 最近业务事件环形缓冲

    # ── 订阅管理 ──

    def subscribe(self, event_type: str, handler: Callable, priority: int = 0) -> None:
        """订阅事件类型

        Args:
            event_type: 事件类型（"private"/"group"/"*"，业务事件用 "biz:{type}"/"biz:*"）
            handler: 处理函数
            priority: 优先级，越高越先执行（安全过滤器等高优先级用 100）
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        handlers = self._subscribers[event_type]
        if priority > 0:
            handlers.insert(0, handler)
        else:
            handlers.append(handler)
        _logger.debug(f"[EventBus] subscribed {event_type}: {handler.__name__} (priority={priority})")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅"""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            _logger.debug(f"[EventBus] unsubscribed {event_type}: {handler.__name__}")

    # ── 事件发布 ──

    async def publish(self, event: LoyanEvent) -> None:
        """发布事件（异步派发，不阻塞调用方）

        1. 通知所有 subscribe 的监听器（兼容旧接口）
        2. 若未被订阅者取消，通过 RuntimeRegistry 路由到对应 Pipeline
        """
        event_type = event.chat_type  # "private" | "group"

        # 路径 A：订阅者通知（安全检查等高优先级订阅者可调用 event.cancel() 阻断）
        for handler in self._subscribers.get(event_type, []):
            if event.cancelled:
                break
            asyncio.create_task(self._safe_call(handler, event))
        if not event.cancelled:
            for handler in self._subscribers.get("*", []):
                asyncio.create_task(self._safe_call(handler, event))

        # 已取消 → 不入 Pipeline
        if event.cancelled:
            return

        # 路径 B：通过 RuntimeRegistry 路由到对应 Runtime 的 Pipeline
        from loyan.core.runtime import RuntimeRegistry, RuntimeContext

        runtime = None
        if event.source:
            runtime = RuntimeRegistry.get_by_tag(event.source)

        if runtime is None:
            # 回退：取第一个注册的 Runtime
            all_runtimes = RuntimeRegistry.get_all()
            if all_runtimes:
                runtime = all_runtimes[0]
            else:
                _logger.warning(
                    f"[EventBus] 无可用 Runtime 处理事件 "
                    f"(source={event.source}, sender={event.sender_id})"
                )
                return

        # 设置消息链路上下文，然后交给 Runtime 的 Pipeline
        token = RuntimeContext.set(runtime)
        try:
            await runtime.pipeline.process(event)
        finally:
            RuntimeContext.reset(token)

    async def _safe_call(self, handler: Callable, event: LoyanEvent) -> None:
        """安全调用 handler，捕获异常防止 Task 崩溃"""
        try:
            result = handler(event)
            if result is not None and hasattr(result, "__await__"):
                await result
        except Exception as e:
            _logger.error(f"[EventBus] handler {handler.__name__} failed: {e}", exc_info=True)

    # ── 业务事件（本轮新增）──

    async def publish_business(self, event: BusinessEvent) -> None:
        """全广播业务事件

        - 按 event.type.value 匹配 biz:{type} 订阅者，同时收 biz:* 通配订阅者
        - 每个订阅者独立 Task 并行执行，错误隔离 + 30s 超时保护（一个挂不影响其他）
        - 订阅者按注册顺序调度：某订阅者调用 event.cancel() 后，后续订阅者不再被调度
        """
        if not event.timestamp:
            event.timestamp = time.time()
        # 发布统计 + 环形缓冲
        self._biz_stats[event.type.value] = self._biz_stats.get(event.type.value, 0) + 1
        self._recent.append(
            {
                "type": event.type.value,
                "source": event.source,
                "adapter_tag": event.adapter_tag,
                "timestamp": event.timestamp,
                "payload": _payload_summary(event.payload),
            }
        )

        handlers = list(self._subscribers.get(f"biz:{event.type.value}", []))
        handlers += list(self._subscribers.get("biz:*", []))
        tasks: List[asyncio.Task] = []
        for handler in handlers:
            if event.cancelled:
                break
            tasks.append(asyncio.create_task(self._safe_biz_call(handler, event)))
            # 让刚创建的 Task 先跑一步：订阅者同步调用 cancel() 时后续订阅者能感知
            await asyncio.sleep(0)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_biz_call(self, handler: Callable, event: BusinessEvent) -> None:
        """安全调用业务订阅者：错误隔离 + 超时保护

        用 asyncio.timeout 而非 wait_for：不引入额外任务切换，
        保证订阅者在当前任务内同步执行的部分（含 cancel()）在
        调度下一个订阅者前生效，cancel 拦截语义才确定。
        """
        try:
            async with asyncio.timeout(self._biz_timeout):
                await self._safe_call(handler, event)
        except asyncio.TimeoutError:
            _logger.error(
                f"[EventBus] biz handler {handler.__name__} 超时 ({self._biz_timeout}s)"
            )

    def biz_stats(self) -> Dict[str, int]:
        """各业务事件类型发布次数（供面板）"""
        return dict(self._biz_stats)

    def recent_events(self) -> List[dict]:
        """最近业务事件列表（环形缓冲，最多 500 条，旧→新）"""
        return list(self._recent)


def _payload_summary(payload: Any) -> Any:
    """Payload 摘要：dataclass 转 dict，dict 原样，其他转 repr（供环形缓冲/面板）"""
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "__dataclass_fields__"):
        return {k: getattr(payload, k) for k in payload.__dataclass_fields__}
    return repr(payload)
