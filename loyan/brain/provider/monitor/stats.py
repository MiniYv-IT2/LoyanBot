"""调用统计 — 每次对话记录用量、耗时、费用，存 SQLite"""

import logging
import time
from collections import defaultdict

from loyan.brain.provider.monitor.cost import calculate
from loyan.core.db_manager import get_db

_logger = logging.getLogger("Brain.monitor.stats")


class StatsCollector:
    def __init__(self):
        self._db = None

    async def init(self):
        self._db = await get_db("llm_usage")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time REAL,
                provider TEXT,
                model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency REAL,
                success INTEGER DEFAULT 1,
                cost REAL DEFAULT 0.0
            )
        """)
        _logger.info("用量统计已初始化")

    async def record(self, provider: str, model: str, tokens: dict, latency: float, success: bool):
        pt = tokens.get("prompt", 0) or tokens.get("prompt_tokens", 0)
        ct = tokens.get("completion", 0) or tokens.get("completion_tokens", 0)
        cost = calculate(provider, model, pt, ct)
        await self._db.execute(
            "INSERT INTO usage (time, provider, model, prompt_tokens, completion_tokens, total_tokens, latency, success, cost) VALUES (?,?,?,?,?,?,?,?,?)",
            time.time(), provider, model, pt, ct, pt + ct, round(latency, 2), 1 if success else 0, cost,
        )

    async def summary(self, hours: int = 24) -> dict:
        cutoff = time.time() - hours * 3600
        row = await self._db.fetchone(
            "SELECT COUNT(*), SUM(success=0), SUM(total_tokens), AVG(latency), SUM(cost) FROM usage WHERE time > ?",
            cutoff,
        )
        total, failed, tokens, avg_lat, total_cost = row or (0, 0, 0, 0, 0)

        rows = await self._db.fetchall(
            "SELECT provider, COUNT(*), SUM(total_tokens), SUM(success=0) FROM usage WHERE time > ? GROUP BY provider",
            cutoff,
        )
        by_provider = {}
        for p, cnt, tk, fl in rows:
            by_provider[p] = {"calls": cnt, "tokens": tk or 0, "failed": fl or 0}

        return {
            "total_calls": total or 0,
            "failed": failed or 0,
            "total_tokens": tokens or 0,
            "avg_latency_ms": round(avg_lat or 0, 2),
            "total_cost": round(total_cost or 0, 6),
            "by_provider": by_provider,
        }

    async def close(self):
        if self._db:
            await self._db.close()


stats = StatsCollector()
