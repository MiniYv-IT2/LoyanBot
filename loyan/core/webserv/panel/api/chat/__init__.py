"""面板 LLM 对话 — 会话 CRUD / 人设列表 / SSE 流式对话"""

import asyncio
import json
import re
import time
import uuid

from loyan.core.db_manager import get_db
from loyan.core.webserv.quart import request, Response, stream_with_context


async def _db():
    return await get_db("chat_sessions")


async def _ensure():
    db = await _db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '新会话',
            created REAL
        )
    """)
    cols = await db.fetchall("PRAGMA table_info(sessions)")
    snames = {c[1] for c in cols}
    if "titled" not in snames:
        await db.execute("ALTER TABLE sessions ADD COLUMN titled INTEGER DEFAULT 0")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created REAL
        )
    """)
    # 迁移：老表补 reasoning / duration 列
    cols = await db.fetchall("PRAGMA table_info(messages)")
    names = {c[1] for c in cols}
    if "reasoning" not in names:
        await db.execute("ALTER TABLE messages ADD COLUMN reasoning TEXT DEFAULT ''")
    if "duration" not in names:
        await db.execute("ALTER TABLE messages ADD COLUMN duration REAL DEFAULT 0")
    # IM 会话分表（与面板表隔离，幂等）
    await db.execute("""
        CREATE TABLE IF NOT EXISTS im_sessions (
            id TEXT PRIMARY KEY,
            created REAL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS im_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created REAL
        )
    """)


def _clean_title(raw: str) -> str:
    """清理标题：去 HTML 符号、去首尾标点，留一句话"""
    s = re.sub(r"<[^>]+>", "", raw or "")
    s = re.sub(r"</?[a-zA-Z][^>]*>", "", s)
    s = s.strip().strip("。.,，!！?？;；:：·~～\"'“”‘’`()（）<>《》")
    return s[:40]


def register_routes(app) -> None:
    @app.route("/api/loyanui/chat/sessions", methods=["GET"])
    async def list_sessions():
        await _ensure()
        db = await _db()
        rows = await db.fetchall("SELECT id, name, created FROM sessions ORDER BY created DESC")
        return {"success": True, "data": [{"id": r[0], "name": r[1], "created": r[2]} for r in rows]}

    @app.route("/api/loyanui/chat/sessions", methods=["POST"])
    async def create_session():
        await _ensure()
        data = await request.get_json() or {}
        sid = data.get("id") or uuid.uuid4().hex[:12]
        name = data.get("name") or "新会话"
        db = await _db()
        await db.execute("INSERT INTO sessions (id, name, created) VALUES (?, ?, ?)",
                         sid, name, time.time())
        return {"success": True, "data": {"id": sid, "name": name}}

    @app.route("/api/loyanui/chat/sessions/<sid>", methods=["DELETE"])
    async def delete_session(sid):
        await _ensure()
        db = await _db()
        await db.execute("DELETE FROM sessions WHERE id = ?", sid)
        await db.execute("DELETE FROM messages WHERE session_id = ?", sid)
        return {"success": True}

    @app.route("/api/loyanui/chat/sessions/<sid>/messages")
    async def session_messages(sid):
        await _ensure()
        db = await _db()
        rows = await db.fetchall(
            "SELECT role, content, reasoning, duration FROM messages WHERE session_id = ? ORDER BY id", sid)
        return {"success": True, "data": [
            {"role": r[0], "content": r[1], "reasoning": r[2] or "", "duration": r[3] or 0}
            for r in rows]}

    @app.route("/api/loyanui/chat/personas")
    async def list_personas():
        from loyan.brain.chat.persona import persona_mgr
        personas = await persona_mgr.list()
        return {"success": True, "data": [{"name": p.name, "prompt": p.prompt} for p in personas]}

    @app.route("/api/loyanui/chat/stream", methods=["POST"])
    async def chat_stream():
        try:
            return await _chat_stream_impl()
        except Exception as e:
            return {"success": False, "message": str(e)}, 500

    # ── 后台任务化：创建 / 订阅 / 列表 / 取消 ──

    @app.route("/api/loyanui/chat/tasks", methods=["POST"])
    async def create_chat_task():
        data = await request.get_json() or {}
        message = (data.get("message") or "").strip()
        if not message:
            return {"success": False, "message": "message_required"}, 400
        session_id = data.get("session_id") or ""
        instance_id = data.get("instance_id") or ""
        persona = data.get("persona") or ""
        strip_think = data.get("strip_think", True)
        from loyan.core.loyan_session.task import task_manager
        await _ensure()
        db = await _db()
        if session_id:
            await db.execute(
                "INSERT INTO messages (session_id, role, content, created) VALUES (?, 'user', ?, ?)",
                session_id, message, time.time())
        task = task_manager.create(
            session_id=session_id,
            message=message,
            provider=instance_id,
            persona=persona,
            strip_think=strip_think,
        )
        return {"success": True, "data": task.snapshot()}

    @app.route("/api/loyanui/chat/tasks", methods=["GET"])
    async def list_chat_tasks():
        from loyan.core.loyan_session.task import task_manager
        return {"success": True, "data": [t.snapshot() for t in task_manager.list_all()]}

    @app.route("/api/loyanui/chat/tasks/<task_id>", methods=["GET"])
    async def get_chat_task(task_id):
        from loyan.core.loyan_session.task import task_manager
        task = task_manager.get(task_id)
        if task is None:
            return {"success": False, "error": "task_not_found"}, 404
        return {"success": True, "data": task.snapshot()}

    @app.route("/api/loyanui/chat/tasks/<task_id>/events", methods=["GET"])
    async def chat_task_events(task_id):
        """SSE 订阅任务事件流（可断线重连：重连时全量补发已累积事件）"""
        from loyan.core.loyan_session.task import task_manager
        task = task_manager.get(task_id)
        if task is None:
            return {"success": False, "error": "task_not_found"}, 404

        async def _gen():
            sent = 0
            while True:
                while sent < len(task.events):
                    yield _sse(task.events[sent])
                    sent += 1
                if task.finished.is_set():
                    yield _sse({"type": "close"})
                    return
                await asyncio.sleep(0.05)

        return Response(stream_with_context(_gen)(), content_type="text/event-stream")

    @app.route("/api/loyanui/chat/tasks/<task_id>/cancel", methods=["POST"])
    async def cancel_chat_task(task_id):
        from loyan.core.loyan_session.task import task_manager
        ok = await task_manager.cancel(task_id)
        return {"success": ok}

    async def _chat_stream_impl():
        data = await request.get_json() or {}
        message = (data.get("message") or "").strip()
        if not message:
            return {"success": False, "message": "message_required"}, 400
        session_id = data.get("session_id") or ""
        instance_id = data.get("instance_id") or ""
        persona = data.get("persona") or ""
        strip_think = data.get("strip_think", True)

        await _ensure()
        db = await _db()
        if session_id:
            await db.execute(
                "INSERT INTO messages (session_id, role, content, created) VALUES (?, 'user', ?, ?)",
                session_id, message, time.time())

        async def _gen():
            from loyan.brain import get_brain
            brain = get_brain()
            started = time.time()
            if not brain.ready:
                yield _sse({"type": "text", "content": "Brain 未初始化，请先配置模型提供商"})
                yield _sse({"type": "done", "usage": {}, "elapsed": round(time.time() - started, 1)})
                return
            reply_parts = []
            reasoning_parts = []
            try:
                async for evt in brain.chat.chat_stream(
                    message=message,
                    session_id=session_id,
                    provider=instance_id,
                    persona=persona,
                    strip_think=strip_think,
                ):
                    if evt.get("type") == "text":
                        reply_parts.append(evt.get("content", ""))
                    elif evt.get("type") == "reasoning":
                        reasoning_parts.append(evt.get("content", ""))
                    yield _sse(evt)
            except Exception as e:
                yield _sse({"type": "text", "content": f"对话失败: {e}"})
            finally:
                elapsed = round(time.time() - started, 1)
                if session_id and reply_parts:
                    await db.execute(
                        "INSERT INTO messages (session_id, role, content, reasoning, duration, created)"
                        " VALUES (?, 'assistant', ?, ?, ?, ?)",
                        session_id, "".join(reply_parts), "".join(reasoning_parts), elapsed, time.time())
                    await _maybe_title(session_id)
                yield _sse({"type": "done", "usage": {}, "elapsed": elapsed})

        gen = stream_with_context(_gen)
        return Response(gen(), content_type="text/event-stream")


async def _maybe_title(session_id: str) -> None:
    """首次交流后自动提取会话标题（静默失败）"""
    try:
        db = await _db()
        row = await db.fetchone("SELECT titled FROM sessions WHERE id = ?", session_id)
        if not row or row[0]:
            return
        rows = await db.fetchall(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id", session_id)
        if len(rows) < 2:
            return
        from loyan.brain import get_brain
        brain = get_brain()
        if not brain.ready:
            return
        transcript = "\n".join(
            f"{'用户' if r[0] == 'user' else 'AI'}: {(r[1] or '')[:300]}" for r in rows)
        title = await brain.chat.chat(
            message=(
                "请为以下对话生成一个简洁的标题，概括主题。"
                f"要求：一句话，不超过 20 字，不要标点结尾，不要任何 HTML 符号。\n\n{transcript}"
            ),
            provider="",
        )
        title = _clean_title(title)
        if title:
            await db.execute(
                "UPDATE sessions SET name = ?, titled = 1 WHERE id = ?", title, session_id)
    except Exception:
        return


def _sse(evt: dict) -> str:
    return f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
