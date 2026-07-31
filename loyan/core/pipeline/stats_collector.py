"""消息统计 Stage — 记录消息量、活跃会话"""

import logging
import time

from loyan.core.pipeline import Stage
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.db_manager import get_db

_logger = logging.getLogger("Core.Stats")


class StatsCollector(Stage):
    force_run: bool = True

    def __init__(self):
        self._db = None

    async def init(self):
        self._db = await get_db("pipeline_stats")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time REAL,
                sender_id TEXT,
                chat_type TEXT
            )
        """)
        _logger.debug("消息统计 Stage 已初始化")

    async def process(self, event: LoyanEvent) -> LoyanEvent:
        if not event or not event.sender_id:
            return event
        try:
            await self._db.execute(
                "INSERT INTO message_log (time, sender_id, chat_type) VALUES (?, ?, ?)",
                time.time(), event.sender_id, event.chat_type or "unknown",
            )
        except Exception as e:
            _logger.warning(f"记录消息统计失败: {e}")
        return event

    async def get_stats(self, hours: int = 24, since: float | None = None) -> dict:
        cutoff = since if since is not None else time.time() - hours * 3600
        total = await self._db.fetchone(
            "SELECT COUNT(*) FROM message_log WHERE time > ?", cutoff
        )
        active = await self._db.fetchone(
            "SELECT COUNT(DISTINCT sender_id) FROM message_log WHERE time > ?",
            time.time() - 300,  # 5 分钟内
        )
        return {
            "total_messages": total[0] if total else 0,
            "active_sessions": active[0] if active else 0,
        }


stats_collector = StatsCollector()
