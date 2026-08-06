"""会话层集成测试 — IM 消息 → 会话落库 → 后台任务 → AI 回复落库 → 恢复

一条龙链路（真实 DB + 真实会话/任务管理器，仅 Brain 用 FakeBrain 注入）：
    群聊消息 → resolve_from_context → get_or_create_im_session
    → add_im_context(用户) → task_manager.create(后台生成)
    → events 累积 → done → 自动落库 assistant 消息
    → 新管理器实例恢复上下文（含用户 + AI 两条）
"""

import asyncio

import pytest

from loyan.core.loyan_session.loyan_session_manager import LoyanSessionManager
from loyan.core.loyan_session.resolve import resolve_from_context
from loyan.core.loyan_session.task.manager import TaskManager
from loyan.core import db_manager
from loyan.core.tools import paths


class FakeBrain:
    def __init__(self, replies):
        self.ready = True
        self._replies = replies
        self.chat = self

    async def chat_stream(self, **kwargs):
        for e in self._replies:
            yield e

    async def chat(self, **kwargs):
        return "标题"


class FakeCtx:
    def __init__(self, platform, instance_id, chat_type, sender_id, target_id):
        from loyan.core.loyan_adapter.identity import IdentityTag
        self.adapter_tag = IdentityTag(platform=platform, instance_id=instance_id,
                                       bot_name="bot")
        self.chat_type = chat_type
        self.sender_id = sender_id
        self.target_id = target_id


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "flow.db")
    monkeypatch.setattr(paths, "get_db_path", lambda name: db_file)
    yield db_file
    asyncio.run(db_manager.close_all())


@pytest.fixture
def brain(monkeypatch):
    brain = FakeBrain([
        {"type": "reasoning", "content": "思考"},
        {"type": "text", "content": "这是 AI 回复"},
        {"type": "done", "usage": {}},
    ])
    monkeypatch.setattr("loyan.brain.get_brain", lambda: brain)
    return brain


def _make_manager():
    m = LoyanSessionManager()
    m._auto_cleanup_interval = 3600
    m._start_auto_cleanup = lambda: None
    return m


@pytest.mark.asyncio
async def test_group_message_full_flow(tmp_db, brain):
    mgr = _make_manager()
    await mgr._ensure_im_tables()
    ctx = FakeCtx("onebot", "inst_a", "group", "u1", "888")

    # 1. 群聊消息 → 统一会话 ID（公共记忆，不带 sub_id）
    sid = resolve_from_context(ctx)
    assert sid == "chat_onebot_inst_a_group_888"

    # 2. 获取/创建 IM 会话 + 用户消息落库
    session = await mgr.get_or_create_im_session(
        ctx.adapter_tag.platform, ctx.adapter_tag.instance_id,
        ctx.chat_type, sender_id=ctx.sender_id, target_id=ctx.target_id)
    assert session.session_id == sid
    await mgr.add_im_context(session, "user", "群友提问")

    # 3. 后台任务执行（真实 TaskManager + FakeBrain）
    tm = TaskManager()
    task = tm.create(sid, "群友提问")
    await asyncio.wait_for(task.finished.wait(), timeout=3)
    assert task.status == "done"

    # 4. 事件流完整：reasoning + text + done（manager 结束时补发 done）
    kinds = [e.get("type") for e in task.events]
    assert "reasoning" in kinds and "text" in kinds
    assert kinds.count("done") >= 1
    # 5. AI 回复自动落库到 im_messages
    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT role, content FROM im_messages WHERE session_id = ? ORDER BY id", sid)
    assert [(r[0], r[1]) for r in rows] == [("user", "群友提问"), ("assistant", "这是 AI 回复")]

    # 6. 模拟重开（新管理器实例）→ 恢复全部上下文
    mgr2 = _make_manager()
    session2 = await mgr2.get_or_create_im_session(
        "onebot", "inst_a", "group", sender_id="u1", target_id="888")
    ctx2 = mgr2.get_im_context(session2)
    assert [m["content"] for m in ctx2] == ["群友提问", "这是 AI 回复"]


@pytest.mark.asyncio
async def test_private_message_flow_with_sub_id(tmp_db, brain):
    mgr = _make_manager()
    await mgr._ensure_im_tables()
    ctx = FakeCtx("telegram", "inst_b", "private", "u9", "u9")

    sid = resolve_from_context(ctx)
    assert sid == "chat_telegram_inst_b_private_u9"

    session = await mgr.get_or_create_im_session(
        "telegram", "inst_b", "private", sender_id="u9", target_id="u9")
    await mgr.add_im_context(session, "user", "私聊问题")

    tm = TaskManager()
    task = tm.create(sid, "私聊问题")
    await asyncio.wait_for(task.finished.wait(), timeout=3)
    assert task.status == "done"

    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT role FROM im_messages WHERE session_id = ?", sid)
    assert [r[0] for r in rows] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_clear_session_resets_context(tmp_db, brain):
    mgr = _make_manager()
    await mgr._ensure_im_tables()
    ctx = FakeCtx("onebot", "inst_a", "group", "u1", "888")
    sid = resolve_from_context(ctx)

    session = await mgr.get_or_create_im_session(
        "onebot", "inst_a", "group", sender_id="u1", target_id="888")
    await mgr.add_im_context(session, "user", "旧消息")

    await mgr.clear_im_session(sid)

    session2 = await mgr.get_or_create_im_session(
        "onebot", "inst_a", "group", sender_id="u1", target_id="888")
    assert mgr.get_im_context(session2) == []
    db = await db_manager.get_db("chat_sessions")
    assert await db.fetchone(
        "SELECT id FROM im_messages WHERE session_id = ?", sid) is None
