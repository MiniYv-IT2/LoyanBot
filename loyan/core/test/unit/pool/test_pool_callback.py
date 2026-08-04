"""AdapterPool 回调契约测试 — 同步/异步回调兼容回归

覆盖历史 bug：pool.start_all 的包装回调是同步函数时，
适配器 `await 回调(event)` 会 await None（qq_official wrapped_event 场景）。
"""

import asyncio
from types import SimpleNamespace

import pytest

from loyan.core.loyan_adapter.pool import AdapterPool
from loyan.core.loyan_adapter.identity import IdentityTag


class _FakeAdapter:
    def __init__(self):
        self.cb = None

    async def start(self, on_event):
        self.cb = on_event

    async def stop(self):
        pass


def _event():
    return SimpleNamespace(source=None, sender_id="1", raw_text="hi")


@pytest.mark.asyncio
async def test_sync_callback_does_not_crash_on_await():
    """底层回调同步返回 None 时，适配器 await 包装回调不应抛 TypeError"""
    pool = AdapterPool()
    fake = _FakeAdapter()
    pool.register(fake, IdentityTag(platform="test", bot_name="t"))

    received = []

    async def sink(event):
        received.append(event)

    await pool.start_all(sink)
    await fake.cb(_event())
    assert len(received) == 1


@pytest.mark.asyncio
async def test_async_callback_still_awaited():
    """底层回调返回 coroutine 时应被 await（不丢事件）"""
    pool = AdapterPool()
    fake = _FakeAdapter()
    pool.register(fake, IdentityTag(platform="test", bot_name="t"))

    received = []

    async def sink(event):
        received.append(event)

    await pool.start_all(sink)
    await fake.cb(_event())
    assert len(received) == 1


@pytest.mark.asyncio
async def test_sync_callback_result_ignored():
    """同步回调（lambda 返回 None）直接执行，不 await 其返回值"""
    pool = AdapterPool()
    fake = _FakeAdapter()
    pool.register(fake, IdentityTag(platform="test", bot_name="t"))

    fired = []

    def sync_sink(event):
        fired.append(event)

    await pool.start_all(sync_sink)
    await fake.cb(_event())
    assert len(fired) == 1
