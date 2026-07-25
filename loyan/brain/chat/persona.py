"""人设管理 — 存储、切换、列表"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from loyan.core.db_manager import get_db

_logger = logging.getLogger("Brain.persona")

_DEFAULT_PERSONA = "default"
_DEFAULT_PROMPT = "你是由 LoyanBot 开发的 AI 助手，名为 LoyanBot AI。请始终友好、专业地回复。"


@dataclass
class Persona:
    name: str
    prompt: str
    created_at: float = 0.0


class PersonaManager:
    def __init__(self):
        self._db = None
        self._current: str = _DEFAULT_PERSONA

    async def init(self):
        self._db = await get_db("persona")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                name TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        # 确保默认人设存在
        import time
        row = await self._db.fetchone("SELECT name FROM personas WHERE name = ?", _DEFAULT_PERSONA)
        if not row:
            await self._db.execute(
                "INSERT INTO personas (name, prompt, created_at) VALUES (?, ?, ?)",
                _DEFAULT_PERSONA, _DEFAULT_PROMPT, time.time(),
            )

    async def list(self) -> list[Persona]:
        rows = await self._db.fetchall("SELECT name, prompt, created_at FROM personas ORDER BY created_at")
        return [Persona(name=r[0], prompt=r[1], created_at=r[2]) for r in rows]

    async def get(self, name: str) -> Optional[Persona]:
        row = await self._db.fetchone("SELECT name, prompt, created_at FROM personas WHERE name = ?", name)
        if not row:
            return None
        return Persona(name=row[0], prompt=row[1], created_at=row[2])

    async def create(self, name: str, prompt: str) -> bool:
        import time
        try:
            await self._db.execute(
                "INSERT INTO personas (name, prompt, created_at) VALUES (?, ?, ?)",
                name, prompt.strip(), time.time(),
            )
            return True
        except Exception:
            return False

    async def delete(self, name: str) -> bool:
        if name == _DEFAULT_PERSONA:
            return False
        await self._db.execute("DELETE FROM personas WHERE name = ?", name)
        return True

    def set_current(self, name: str):
        self._current = name

    @property
    def current(self) -> str:
        return self._current

    async def current_prompt(self) -> str:
        p = await self.get(self._current)
        return p.prompt if p else _DEFAULT_PROMPT


persona_mgr = PersonaManager()
