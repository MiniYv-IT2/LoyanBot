"""ChatTask — 单次后台生成任务

持有任务状态: running → done | error | cancelled。
事件流: task.events 累积全部事件 (断线重连全量补发), finished 事件标记完成。
"""

import asyncio
import time
import uuid
from typing import List, Optional


class ChatTask:
    def __init__(self, session_id: str, task_id: Optional[str] = None):
        self.task_id = task_id or uuid.uuid4().hex[:12]
        self.session_id = session_id
        self.status = "running"
        self.events: List[dict] = []
        self.created = time.time()
        self.finished = asyncio.Event()

    @property
    def is_active(self) -> bool:
        return self.status == "running"

    def snapshot(self) -> dict:
        """供面板列表展示的最小字段"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "status": self.status,
            "created": round(self.created, 1),
        }
