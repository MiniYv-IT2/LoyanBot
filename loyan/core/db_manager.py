import os
import re
import asyncio
from typing import Optional, List
import aiosqlite

_db_instances: dict = {}
_db_instances_lock = asyncio.Lock()


def _sanitize(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff\-]', '_', name)


class DBHandle:
    def __init__(self, plugin_name: str, db_path: str):
        self._name = plugin_name
        self._path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def _ensure(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            self._conn = await aiosqlite.connect(self._path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")

    async def execute(self, sql: str, *params) -> int:
        async with self._lock:
            await self._ensure()
            cursor = await self._conn.execute(sql, params or ())
            await self._conn.commit()
            return cursor.lastrowid

    async def executemany(self, sql: str, params_list: List[tuple]) -> None:
        async with self._lock:
            await self._ensure()
            await self._conn.executemany(sql, params_list)
            await self._conn.commit()

    async def fetchall(self, sql: str, *params) -> list:
        async with self._lock:
            await self._ensure()
            cursor = await self._conn.execute(sql, params or ())
            return await cursor.fetchall()

    async def fetchone(self, sql: str, *params):
        async with self._lock:
            await self._ensure()
            cursor = await self._conn.execute(sql, params or ())
            return await cursor.fetchone()

    async def close(self):
        async with self._lock:
            if self._conn is not None:
                await self._conn.close()
                self._conn = None


async def get_db(plugin_name: str, db_name: str = None) -> DBHandle:
    """获取数据库句柄

    Args:
        plugin_name: 插件名（显示名或目录名均可，自动归一化到目录名）
        db_name: 自定义数据库文件名（可选，不传默认 {目录名}.db）
                 支持一个插件多个库：get_db("Music_Plugin", "history")

    插件数据库固定位于 storage/data/plugins/{插件目录名}/，
    框架数据库位于 storage/data/。
    """
    safe = _sanitize(plugin_name)
    if not safe:
        safe = "unnamed"
    from loyan.core.tools.paths import get_db_path, get_plugin_data_dir
    dir_name = _plugin_dir_name(safe)
    if dir_name:
        file_name = _sanitize(db_name) if db_name else dir_name
        path = os.path.join(get_plugin_data_dir(dir_name), f"{file_name}.db")
    else:
        file_name = _sanitize(db_name) if db_name else safe
        path = get_db_path(file_name)

    async with _db_instances_lock:
        if path not in _db_instances:
            _db_instances[path] = DBHandle(plugin_name, path)
        return _db_instances[path]


def _plugin_dir_name(name: str) -> Optional[str]:
    """按显示名或注册名查找插件目录名（英文标识）；非插件返回 None"""
    try:
        from loyan.core.plugin_manager import plugin_manager
        for p in plugin_manager.registry:
            if p.get("name") == name:
                return os.path.basename(p.get("plugin_path", ""))
            if os.path.basename(p.get("plugin_path", "")) == name:
                return name
    except Exception:
        pass
    return None


async def close_all():
    async with _db_instances_lock:
        for handle in _db_instances.values():
            await handle.close()
        _db_instances.clear()
