"""TaskManager — 后台聊天任务管理

单例 task_manager, 管理 ChatTask 生命周期:
    - create: 启动后台生成任务, 立即返回 task (不阻塞)
    - get / list_active: 查询任务 (重开页面恢复用)
    - cancel: 取消运行中任务
任务执行: 消费 brain.chat.chat_stream 事件 → 累积 events → 完成落库 (面板/IM 分表)。
"""

import asyncio
import time
from typing import Dict, List, Optional

from loyan.core.loyan_session.task.chat_task import ChatTask

_KEEP_MAX = 100


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, ChatTask] = {}
        self._runners: Dict[str, asyncio.Task] = {}

    def create(
        self,
        session_id: str,
        message: str,
        provider: str = "",
        persona: str = "",
        strip_think: bool = True,
    ) -> ChatTask:
        task = ChatTask(session_id)
        self._tasks[task.task_id] = task
        runner = asyncio.ensure_future(self._run(task, message, provider, persona, strip_think))
        self._runners[task.task_id] = runner
        self._prune()
        return task

    def get(self, task_id: str) -> Optional[ChatTask]:
        return self._tasks.get(task_id)

    def list_active(self) -> List[ChatTask]:
        return [t for t in self._tasks.values() if t.is_active]

    def list_all(self) -> List[ChatTask]:
        return list(self._tasks.values())

    async def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or not task.is_active:
            return False
        task.status = "cancelled"
        runner = self._runners.get(task_id)
        if runner is not None and not runner.done():
            runner.cancel()
        task.finished.set()
        return True

    async def _run(self, task, message, provider, persona, strip_think) -> None:
        from loyan.brain import get_brain
        brain = get_brain()
        started = time.time()
        reply_parts: List[str] = []
        reasoning_parts: List[str] = []
        try:
            if not brain.ready:
                task.events.append({"type": "text", "content": "Brain 未初始化，请先配置模型提供商"})
            else:
                async for evt in brain.chat.chat_stream(
                    message=message,
                    session_id=task.session_id,
                    provider=provider,
                    persona=persona,
                    strip_think=strip_think,
                ):
                    task.events.append(evt)
                    if evt.get("type") == "text":
                        reply_parts.append(evt.get("content", ""))
                    elif evt.get("type") == "reasoning":
                        reasoning_parts.append(evt.get("content", ""))
            task.status = "done"
        except asyncio.CancelledError:
            task.status = "cancelled"
        except Exception as e:
            task.status = "error"
            task.events.append({"type": "text", "content": f"对话失败: {e}"})
        finally:
            elapsed = round(time.time() - started, 1)
            task.events.append({"type": "done", "usage": {}, "elapsed": elapsed})
            try:
                if task.session_id and reply_parts:
                    await self._persist(task.session_id, "".join(reply_parts),
                                        "".join(reasoning_parts), elapsed)
                    await self._maybe_title(task.session_id)
            except BaseException:
                pass
            task.finished.set()

    async def _persist(self, session_id: str, content: str, reasoning: str, elapsed: float) -> None:
        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
        table = self._table_for(session_id)
        if table == "messages":
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT, role TEXT, content TEXT,
                    reasoning TEXT DEFAULT '', duration REAL DEFAULT 0, created REAL)
            """)
            await db.execute(
                "INSERT INTO messages (session_id, role, content, reasoning, duration, created)"
                " VALUES (?, 'assistant', ?, ?, ?, ?)",
                session_id, content, reasoning, elapsed, time.time())
        else:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS im_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT, role TEXT, content TEXT, created REAL)
            """)
            await db.execute(
                "INSERT INTO im_messages (session_id, role, content, created)"
                " VALUES (?, 'assistant', ?, ?)",
                session_id, content, time.time())

    async def _maybe_title(self, session_id: str) -> None:
        """首次交流后自动提取会话标题（静默失败）；im_ 表无标题字段则跳过"""
        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
        if self._table_for(session_id) != "messages":
            return
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
        import re
        s = re.sub(r"<[^>]+>", "", title or "")
        title = s.strip().strip("。.,，!！?？;；:：·~～\"'“”‘’`()（）<>《》")[:40]
        if title:
            await db.execute(
                "UPDATE sessions SET name = ?, titled = 1 WHERE id = ?", title, session_id)

    @staticmethod
    def _table_for(session_id: str) -> str:
        if session_id.startswith("chat_") and not session_id.startswith("chat_panel_web_"):
            return "im_messages"
        return "messages"

    def _prune(self) -> None:
        if len(self._tasks) <= _KEEP_MAX:
            return
        done_tasks = [t for t in self._tasks.values() if not t.is_active]
        for t in done_tasks[: len(self._tasks) - _KEEP_MAX]:
            self._tasks.pop(t.task_id, None)


task_manager = TaskManager()