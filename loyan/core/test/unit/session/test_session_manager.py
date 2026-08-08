"""LoyanSessionManager IM 会话单元测试 — 建/取/清/落库

用临时 DB 文件 + monkeypatch get_db_path，不碰真实存储。
"""

import asyncio

import pytest

from loyan.core.loyan_session.loyan_session_manager import LoyanSessionManager
from loyan.core import db_manager
from loyan.core.tools import paths


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(paths, "get_db_path", lambda name: db_file)
    yield db_file
    # 清理 DB 实例缓存，避免跨测试复用旧连接
    asyncio.run(db_manager.close_all())


@pytest.fixture
def mgr(tmp_db, monkeypatch):
    m = LoyanSessionManager()
    # 关闭自动清理循环，避免悬挂任务
    m._auto_cleanup_interval = 3600
    monkeypatch.setattr(m, "_start_auto_cleanup", lambda: None)
    return m


@pytest.mark.asyncio
async def test_ensure_im_tables_creates(tmp_db):
    m = LoyanSessionManager()
    await m._ensure_im_tables()
    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('im_sessions','im_messages')")
    assert {r[0] for r in rows} == {"im_sessions", "im_messages"}


@pytest.mark.asyncio
async def test_get_or_create_im_session_persists(mgr):
    await mgr._ensure_im_tables()
    s1 = await mgr.get_or_create_im_session("onebot", "inst_a", "private", sender_id="10001")
    assert s1.session_id == "chat_onebot_inst_a_private_10001"
    # 同一会话复用（内存缓存）
    s2 = await mgr.get_or_create_im_session("onebot", "inst_a", "private", sender_id="10001")
    assert s2 is s1
    # 落库
    db = await db_manager.get_db("chat_sessions")
    row = await db.fetchone("SELECT id FROM im_sessions WHERE id = ?", s1.session_id)
    assert row is not None


@pytest.mark.asyncio
async def test_add_im_context_persists(mgr):
    await mgr._ensure_im_tables()
    s = await mgr.get_or_create_im_session("telegram", "inst_b", "group", target_id="777")
    await mgr.add_im_context(s, "user", "你好")
    await mgr.add_im_context(s, "assistant", "你好呀")
    db = await db_manager.get_db("chat_sessions")
    rows = await db.fetchall(
        "SELECT role, content FROM im_messages WHERE session_id = ? ORDER BY id", s.session_id)
    assert [(r[0], r[1]) for r in rows] == [("user", "你好"), ("assistant", "你好呀")]


@pytest.mark.asyncio
async def test_get_im_context_restored_from_db(mgr):
    await mgr._ensure_im_tables()
    s = await mgr.get_or_create_im_session("telegram", "inst_b", "group", target_id="777")
    await mgr.add_im_context(s, "user", "问题")
    # 新管理器实例 → 从 DB 恢复上下文
    m2 = LoyanSessionManager()
    s2 = await m2.get_or_create_im_session("telegram", "inst_b", "group", target_id="777")
    ctx = m2.get_im_context(s2)
    assert [m["content"] for m in ctx] == ["问题"]
    assert all(m["role"] in ("user", "assistant") for m in ctx)


@pytest.mark.asyncio
async def test_clear_im_session_removes_rows(mgr):
    await mgr._ensure_im_tables()
    s = await mgr.get_or_create_im_session("onebot", "inst_a", "private", sender_id="9")
    await mgr.add_im_context(s, "user", "x")
    await mgr.clear_im_session(s.session_id)
    db = await db_manager.get_db("chat_sessions")
    assert await db.fetchone("SELECT id FROM im_sessions WHERE id = ?", s.session_id) is None
    assert await db.fetchone(
        "SELECT id FROM im_messages WHERE session_id = ?", s.session_id) is None
    assert s.session_id not in mgr._sessions


@pytest.mark.asyncio
async def test_get_or_create_im_session_no_peer_raises(mgr):
    await mgr._ensure_im_tables()
    with pytest.raises(ValueError):
        await mgr.get_or_create_im_session("onebot", "inst_a", "private")


def test_generate_session_id_group_shared_default():
    """群聊默认公共记忆：target 相同 → 会话 ID 相同（不区分 sender）"""
    m = LoyanSessionManager()
    a = m._generate_session_id("u1", "888")
    b = m._generate_session_id("u2", "888")
    assert a == b == "group:888"


@pytest.mark.asyncio
async def test_cleanup_expired_im_rows(mgr):
    """DB 过期行清理：过期且内存无 → 删；内存活跃 → 留"""
    await mgr._ensure_im_tables()
    db = await db_manager.get_db("chat_sessions")

    # 会话 A: 过期(created 很早) 且不在内存
    await db.execute("INSERT INTO im_sessions (id, created) VALUES (?, ?)",
                     "chat_onebot_a_private_old", 1.0)
    await db.execute("INSERT INTO im_messages (session_id, role, content, created) VALUES (?, 'user', 'x', 1.0)",
                     "chat_onebot_a_private_old")
    # 会话 B: created 很旧但内存活跃(get_or_create 会刷新 created 吗? 不会, 用新会话模拟活跃)
    s_b = await mgr.get_or_create_im_session("onebot", "b", "private", sender_id="active")
    # 把 B 的 created 改老, 但保留在内存中
    await db.execute("UPDATE im_sessions SET created = ? WHERE id = ?", 1.0, s_b.session_id)

    mgr._default_expire_minutes = 30
    n = await mgr.cleanup_expired_im_rows()
    assert n == 1
    # 过期行已删
    assert await db.fetchone("SELECT id FROM im_sessions WHERE id = ?",
                             "chat_onebot_a_private_old") is None
    assert await db.fetchone(
        "SELECT id FROM im_messages WHERE session_id = ?",
        "chat_onebot_a_private_old") is None
    # 内存活跃的 B 保留
    assert await db.fetchone("SELECT id FROM im_sessions WHERE id = ?", s_b.session_id) is not None
