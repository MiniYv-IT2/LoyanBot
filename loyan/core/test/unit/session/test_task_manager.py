"""TaskManager 单元测试 — 后台任务生命周期 + 分表落库

用 FakeBrain 注入（monkeypatch loyan.brain.get_brain），不碰真实 LLM。
"""

import asyncio

import pytest

from loyan.core.loyan_session.task.chat_task import ChatTask
from loyan.core.loyan_session.task.manager import TaskManager
from loyan.core import db_manager
from loyan.core.tools import paths


class FakeBrain:
    """假 Brain：ready=True，brain.chat.chat_stream 产出固定事件"""

    def __init__(self, events):
        self.ready = True
        self._events = events
        self.chat = self

    async def chat_stream(self, **kwargs):
        for e in self._events:
            yield e

    async def chat(self, **kwargs):
        return "标题"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "task.db")
    monkeypatch.setattr(paths, "get_db_path", lambda name: db_file)
    yield db_file
    asyncio.run(db_manager.close_all())


@pytest.fixture
def fake_brain(monkeypatch):
    def _install(events):
        brain = FakeBrain(events)
        monkeypatch.setattr("loyan.brain.get_brain", lambda: brain)
        return brain
    return _install


def test_chat_task_lifecycle():
    t = ChatTask("chat_onebot_i1_private_1")
    assert t.status == "running"
    assert t.is_active
    assert not t.finished.is_set()
    snap = t.snapshot()
    assert snap["task_id"] == t.task_id
    assert snap["session_id"] == t.session_id


@pytest.mark.asyncio
async def test_create_finish_persists_im_table(tmp_db, fake_brain):
    fake_brain([{"type": "text", "content": "回答"}, {"type": "done", "usage": {}}])
    m = TaskManager()
    t = m.create("chat_telegram_i1_group_777", "问题")
    await asyncio.wait_for(t.finished.wait(), timeout=3)

    assert t.status == "done"
    texts = [e["content"] for e in t.events if e.get("type") == "text"]
    assert "".join(texts) == "回答"
    assert t.events[-1]["type"] == "done"

    # 落库到 im_messages（IM 会话走 im 分表）
    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT role, content FROM im_messages WHERE session_id = ?", t.session_id)
    assert len(rows) == 1
    assert rows[0][0] == "assistant"
    assert rows[0][1] == "回答"


@pytest.mark.asyncio
async def test_create_finish_persists_panel_table(tmp_db, fake_brain):
    fake_brain([{"type": "text", "content": "面板回复"}])
    m = TaskManager()
    t = m.create("chat_panel_web_abc", "问题")
    await asyncio.wait_for(t.finished.wait(), timeout=3)

    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT role, content FROM messages WHERE session_id = ?", t.session_id)
    assert len(rows) == 1
    assert rows[0][1] == "面板回复"


@pytest.mark.asyncio
async def test_cancel_interrupts_runner(tmp_db, fake_brain):
    started = asyncio.Event()

    class SlowBrain(FakeBrain):
        async def chat_stream(self, **kwargs):
            started.set()
            await asyncio.sleep(30)
            yield {"type": "text", "content": "永远不会到"}

    brain = SlowBrain([])
    m = TaskManager()
    # 直接安装 SlowBrain
    import loyan.brain as brain_mod
    orig = brain_mod.get_brain
    brain_mod.get_brain = lambda: brain
    try:
        t = m.create("chat_onebot_i1_private_1", "问题")
        await asyncio.wait_for(started.wait(), timeout=3)
        ok = await m.cancel(t.task_id)
        assert ok is True
        await asyncio.wait_for(t.finished.wait(), timeout=3)
        assert t.status == "cancelled"
        assert t not in m.list_active()
    finally:
        brain_mod.get_brain = orig


def test_table_for_routing():
    assert TaskManager._table_for("chat_panel_web_abc") == "messages"
    assert TaskManager._table_for("chat_telegram_i1_group_1") == "im_messages"
    assert TaskManager._table_for("private:1") == "messages"


@pytest.mark.asyncio
async def test_get_and_list(tmp_db, fake_brain):
    fake_brain([{"type": "text", "content": "x"}])
    m = TaskManager()
    t = m.create("chat_onebot_i1_private_1", "q")
    assert m.get(t.task_id) is t
    assert t in m.list_active()
    await asyncio.wait_for(t.finished.wait(), timeout=3)
    assert m.get(t.task_id) is t
    assert t not in m.list_active()
    assert t in m.list_all()


@pytest.mark.asyncio
async def test_brain_not_ready_reports(tmp_db, monkeypatch):
    class NotReadyBrain(FakeBrain):
        def __init__(self, events):
            super().__init__(events)
            self.ready = False
    monkeypatch.setattr("loyan.brain.get_brain", lambda: NotReadyBrain([]))
    m = TaskManager()
    t = m.create("chat_onebot_i1_private_1", "q")
    await asyncio.wait_for(t.finished.wait(), timeout=3)
    assert t.status == "done"
    texts = "".join(e.get("content", "") for e in t.events if e.get("type") == "text")
    assert "Brain 未初始化" in texts
