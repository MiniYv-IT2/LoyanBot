import os
import json
import asyncio
import logging
import time
from typing import Optional, Dict, List, Any
from threading import Lock


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
from .loyan_session import LoyanSession

try:
    from loyan.core.config import LOG_LEVEL
except ImportError:
    LOG_LEVEL = "INFO"

_DEFAULT_CONFIG = {
    "default_expire_minutes": 30,
    "auto_cleanup_interval": 60,
    "max_context_messages": 50,
    "shared_group_session": True
}


class LoyanSessionManager:
    """Loyan会话管理器 - 管理所有会话"""

    def __init__(self):
        self._sessions: Dict[str, LoyanSession] = {}
        self._lock = Lock()
        self._logger = logging.getLogger("Core.Session")
        self._config = dict(_DEFAULT_CONFIG)
        self._default_expire_minutes = self._config["default_expire_minutes"]
        self._max_context_messages = self._config["max_context_messages"]
        self._auto_cleanup_interval = self._config["auto_cleanup_interval"]
        self._shared_group_session = self._config["shared_group_session"]
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self, config_path: Optional[str] = None) -> None:
        self._config = await self._load_config(config_path)
        self._default_expire_minutes = self._config.get("default_expire_minutes", 30)
        self._max_context_messages = self._config.get("max_context_messages", 50)
        self._auto_cleanup_interval = self._config.get("auto_cleanup_interval", 60)
        self._shared_group_session = self._config.get("shared_group_session", True)
        await self._ensure_im_tables()
        self._start_auto_cleanup()

    async def _ensure_im_tables(self) -> None:
        """确保 im_sessions / im_messages 分表存在（面板表由 panel api 管理，互不干扰）"""
        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
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

    async def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "config",
                "loyan_session_config.json"
            )
        if os.path.exists(config_path):
            try:
                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, lambda: _read_json(config_path))
                if data:
                    return data
            except Exception as e:
                self._logger.warning(f"加载配置失败: {e}，使用默认配置")
        return dict(_DEFAULT_CONFIG)

    def _start_auto_cleanup(self) -> None:
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self._auto_cleanup_interval)
                    self.cleanup_expired_sessions()
                except asyncio.CancelledError:
                    break

        self._cleanup_task = asyncio.ensure_future(cleanup_loop())

    def _generate_session_id(self, sender_id: Optional[str], target_id: Optional[str]) -> str:
        """生成会话ID"""
        if target_id:
            if self._shared_group_session:
                return f"group:{target_id}"
            else:
                return f"{target_id}:{sender_id}" if sender_id else f"group:{target_id}"
        return f"private:{sender_id}" if sender_id else "private:global"

    def create_session(
        self,
        sender_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> LoyanSession:
        """创建新会话"""
        session_id = self._generate_session_id(sender_id or "", target_id)
        session = LoyanSession(
            session_id=session_id,
            sender_id=sender_id,
            target_id=target_id,
            expire_minutes=self._default_expire_minutes
        )

        with self._lock:
            self._sessions[session_id] = session

        self._logger.debug(f"创建会话: {session_id}")
        return session

    def get_session(
        self,
        sender_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> Optional[LoyanSession]:
        """获取会话（不存在返回None）"""
        session_id = self._generate_session_id(sender_id, target_id)
        session = self._sessions.get(session_id)

        if session and session.is_expired():
            return None

        if session:
            session.refresh(self._default_expire_minutes)

        return session

    def get_or_create_session(
        self,
        sender_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> LoyanSession:
        """获取或创建会话"""
        session = self.get_session(sender_id, target_id)
        if session is None:
            session = self.create_session(sender_id, target_id)
        return session

    def destroy_session(
        self,
        sender_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> bool:
        """销毁会话"""
        session_id = self._generate_session_id(sender_id, target_id)

        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._logger.debug(f"销毁会话: {session_id}")
                return True

        return False

    # ── IM 会话（统一会话层，落库 im_sessions / im_messages） ──

    async def get_or_create_im_session(
        self,
        platform: str,
        instance_id: str,
        chat_type: str,
        sender_id: str = "",
        target_id: str = "",
        sub_id: Optional[str] = None,
    ) -> "LoyanSession":
        """获取或创建 IM 会话（内存缓存 + 落库）；群聊默认公共记忆（无 sub_id）"""
        from loyan.core.loyan_session.resolve import resolve_im_session_id
        peer_id = target_id if chat_type == "group" else sender_id
        session_id = resolve_im_session_id(platform, instance_id, chat_type, peer_id, sub_id)
        if not session_id:
            raise ValueError("cannot resolve im session id without peer")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None and not session.is_expired():
                return session

        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
        row = await db.fetchone("SELECT created FROM im_sessions WHERE id = ?", session_id)
        if row is None:
            await db.execute("INSERT INTO im_sessions (id, created) VALUES (?, ?)", session_id, time.time())
            session = LoyanSession(
                session_id=session_id,
                sender_id=sender_id or None,
                target_id=target_id or None,
                expire_minutes=self._default_expire_minutes,
            )
        else:
            session = LoyanSession(
                session_id=session_id,
                sender_id=sender_id or None,
                target_id=target_id or None,
                expire_minutes=self._default_expire_minutes,
            )
            rows = await db.fetchall(
                "SELECT role, content FROM im_messages WHERE session_id = ? ORDER BY id", session_id)
            for role, content in rows:
                if content:
                    session.context.append({"role": role, "content": content})

        with self._lock:
            self._sessions[session_id] = session
        return session

    async def add_im_context(self, session: "LoyanSession", role: str, content: str) -> None:
        """向 IM 会话追加一条上下文并落库"""
        session.add_context(role, content)
        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
        await db.execute(
            "INSERT INTO im_messages (session_id, role, content, created) VALUES (?, ?, ?, ?)",
            session.session_id, role, content, time.time())

    async def clear_im_session(self, session_id: str) -> None:
        """清空 IM 会话（删 im_messages / im_sessions 行，内存同步移除）"""
        from loyan.core.db_manager import get_db
        db = await get_db("chat_sessions")
        await db.execute("DELETE FROM im_messages WHERE session_id = ?", session_id)
        await db.execute("DELETE FROM im_sessions WHERE id = ?", session_id)
        with self._lock:
            self._sessions.pop(session_id, None)

    def get_im_context(self, session: "LoyanSession", limit: Optional[int] = None) -> List[Dict[str, str]]:
        """获取 IM 会话上下文（AI 对话用，含 system 过滤）"""
        msgs = session.get_context(limit or self._max_context_messages)
        return [m for m in msgs if m.get("role") in ("user", "assistant")]

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话，返回清理数量"""
        expired_count = 0

        with self._lock:
            expired_ids = [
                sid for sid, s in self._sessions.items()
                if s.is_expired()
            ]
            for sid in expired_ids:
                del self._sessions[sid]
                expired_count += 1

        if expired_count > 0:
            self._logger.debug(f"清理了 {expired_count} 个过期会话")

        return expired_count

    def get_all_sessions(self) -> List[LoyanSession]:
        """获取所有会话"""
        with self._lock:
            return list(self._sessions.values())

    def shutdown(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# ========== 全局实例和便捷函数 ==========
_manager: Optional[LoyanSessionManager] = None


async def loyan_init_session_manager(config_path: Optional[str] = None) -> LoyanSessionManager:
    global _manager
    if _manager is None:
        _manager = LoyanSessionManager()
    await _manager.initialize(config_path)
    return _manager


def loyan_get_session_manager() -> LoyanSessionManager:
    global _manager
    if _manager is None:
        _manager = LoyanSessionManager()
    return _manager


def loyan_get_session(sender_id: Optional[str] = None, target_id: Optional[str] = None) -> Optional[LoyanSession]:
    """获取会话"""
    return loyan_get_session_manager().get_session(sender_id, target_id)


def loyan_get_or_create_session(sender_id: Optional[str] = None, target_id: Optional[str] = None) -> LoyanSession:
    """获取或创建会话"""
    return loyan_get_session_manager().get_or_create_session(sender_id, target_id)


def loyan_create_session(sender_id: Optional[str] = None, target_id: Optional[str] = None) -> LoyanSession:
    """创建会话"""
    return loyan_get_session_manager().create_session(sender_id, target_id)


def loyan_destroy_session(sender_id: Optional[str] = None, target_id: Optional[str] = None) -> bool:
    """销毁会话"""
    return loyan_get_session_manager().destroy_session(sender_id, target_id)


def loyan_add_context(
    session: LoyanSession,
    role: str,
    content: str
) -> None:
    """添加AI对话上下文"""
    session.add_context(role, content)


def loyan_get_context(
    session: LoyanSession,
    limit: Optional[int] = None
) -> List[Dict[str, str]]:
    """获取AI对话上下文"""
    if limit is None:
        limit = loyan_get_session_manager()._max_context_messages
    return session.get_context(limit)


def loyan_clear_context(session: LoyanSession) -> None:
    """清空对话上下文"""
    session.clear_context()


async def loyan_get_or_create_im_session(
    platform: str,
    instance_id: str,
    chat_type: str,
    sender_id: str = "",
    target_id: str = "",
    sub_id: Optional[str] = None,
) -> LoyanSession:
    """获取或创建 IM 会话（统一会话层）"""
    return await loyan_get_session_manager().get_or_create_im_session(
        platform, instance_id, chat_type, sender_id, target_id, sub_id)


async def loyan_add_im_context(session: LoyanSession, role: str, content: str) -> None:
    """向 IM 会话追加上下文并落库"""
    await loyan_get_session_manager().add_im_context(session, role, content)


async def loyan_clear_im_session(session_id: str) -> None:
    """清空 IM 会话"""
    await loyan_get_session_manager().clear_im_session(session_id)


def loyan_set_state(session: LoyanSession, key: str, value: Any) -> None:
    """设置会话状态"""
    session.set_state(key, value)


def loyan_get_state(session: LoyanSession, key: str, default: Any = None) -> Any:
    """获取会话状态"""
    return session.get_state(key, default)


def loyan_session(
    auto_refresh: bool = True,
    expire_minutes: Optional[int] = 0
):
    """
    Loyan会话装饰器 - 自动管理会话

    使用示例:
        @loyan_session()
        def handle_message(data: dict, session: LoyanSession):
            # session会自动注入
            loyan_add_context(session, "user", data["text"])
            # ...

    参数:
        auto_refresh: 自动刷新过期时间
        expire_minutes: 自定义过期时间（分钟）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            sender_id = kwargs.get("sender_id")
            target_id = kwargs.get("target_id")

            if not sender_id and not target_id and len(args) > 0:
                first_arg = args[0]
                if isinstance(first_arg, dict):
                    sender_id = first_arg.get("sender_id")
                    target_id = first_arg.get("target_id")

            if not sender_id and not target_id:
                return func(*args, **kwargs)

            session = loyan_get_or_create_session(sender_id, target_id)

            if auto_refresh:
                manager = loyan_get_session_manager()
                session.refresh(expire_minutes or manager._default_expire_minutes)

            kwargs["session"] = session

            return func(*args, **kwargs)

        return wrapper
    return decorator
