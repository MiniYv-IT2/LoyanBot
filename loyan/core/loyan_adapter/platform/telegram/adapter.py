"""Telegram 适配器 — 基于 python-telegram-bot"""
import asyncio
import logging
from typing import Callable, List, Optional
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg, LoyanText

from .gateway import TelegramGateway
from .auth import validate_token
from .sender import send_message, send_chat_action, send_split_text, send_media_group
from .bind import AdminBinding

_logger = logging.getLogger("Adapter.Telegram")


class TelegramAdapter(LoyanAdapter):
    def __init__(
        self,
        token: str = "",
        proxy_url: str = "",
        webhook_url: str = "",
        webhook_port: int = 8443,
        config_path: str = "",
        conn_type: str = "",
    ):
        self._token = token
        self._proxy_url = proxy_url
        self._webhook_url = webhook_url
        self._webhook_port = webhook_port
        self._config_path = config_path
        self._conn_type = conn_type or ("webhook" if webhook_url else "polling")
        self._gateway: Optional[TelegramGateway] = None
        self._gateway_task: Optional[asyncio.Task] = None
        self._bot_info: Optional[dict] = None
        self._bot: Optional[Bot] = None
        self._admin_binding = AdminBinding(config_path)
        self._dedup: set = set()
        self._start_time: Optional[datetime] = None
        self._send_count: int = 0

    @property
    def is_connected(self) -> bool:
        gw = getattr(self, '_gateway', None)
        if gw:
            app = getattr(gw, '_app', None)
            if app is not None and getattr(app, 'running', False):
                return True
        return False

    async def start(self, on_event: Callable[[LoyanEvent], None]) -> None:
        self._start_time = datetime.now()
        self._bot_info = await validate_token(self._token, self._proxy_url)
        if not self._bot_info:
            return
        self._admin_binding.load()
        from telegram import Bot
        from telegram.request import HTTPXRequest
        if self._proxy_url:
            self._bot = Bot(self._token, request=HTTPXRequest(proxy=self._proxy_url, connect_timeout=10))
        else:
            self._bot = Bot(self._token)
        self._gateway = TelegramGateway(
            token=self._token, proxy_url=self._proxy_url,
            on_event=on_event, tag=self.tag,
            webhook_url=self._webhook_url or None,
            webhook_port=self._webhook_port,
            parse_business=self.parse_business_event,
        )
        self._gateway_task = asyncio.ensure_future(self._gateway.start())

    async def stop(self) -> None:
        if self._gateway:
            await self._gateway.stop()
        if self._gateway_task and not self._gateway_task.done():
            self._gateway_task.cancel()
        if self._gateway:
            self._gateway = None
            self._dedup.clear()

    async def send(self, target: str, segments: List[LoyanMsg], chat_type: str) -> bool:
        if not self._bot:
            return False
            return False
        try:
            ok = await send_message(self._bot, target, segments, chat_type)
            if ok:
                self._send_count += 1
            return ok
        except TelegramError:
            return False

    async def get_platform_info(self) -> dict:
        info = self._bot_info or {}
        uptime = ""
        if self._start_time:
            d = datetime.now() - self._start_time
            uptime = f"{int(d.total_seconds()//3600)}h{int((d.total_seconds()%3600)//60)}m"
        return {
            "friend_count": None,
            "group_count": None,
            "platform": "Telegram",
            "protocol_version": "Bot API 8.x",
            "nickname": info.get("username", ""),
            "bot_id": info.get("id"),
            "uptime": uptime,
            "send_count": self._send_count,
            "admin_count": len(self._admin_binding.admin_ids),
        }

    async def call_api(self, action: str, params: dict = None) -> Optional[dict]:
        return None

    def parse_business_event(self, raw) -> Optional["BusinessEvent"]:
        """Telegram Update → BusinessEvent（委托 business.py）"""
        from loyan.core.loyan_adapter.platform.telegram.business import parse_telegram_business
        return parse_telegram_business(raw)

    def is_admin(self, user_id: str) -> bool:
        return self._admin_binding.is_admin(user_id)

    def add_admin(self, user_id: str) -> bool:
        return self._admin_binding.add_admin(user_id)

    def remove_admin(self, user_id: str) -> bool:
        return self._admin_binding.remove_admin(user_id)

from .factory import create_adapter

from .factory import create_adapter  # noqa: E402, F401
