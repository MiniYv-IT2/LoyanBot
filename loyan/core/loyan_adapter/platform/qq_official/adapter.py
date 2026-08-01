"""QQ 官方个人机器人适配器 — 统一入口

实现 LoyanAdapter 抽象类，整合：
- QQOfficialAPI: HTTP REST API（OAuth2、发消息）
- QQOfficialGateway: WebSocket Gateway 连接管理
- protocol: 协议转换（官方格式 ↔ LoyanEvent/LoyanMsg）
- sender: 消息发送高层封装
- bind: 主从绑定管理

用法:
    from loyan.core.loyan_adapter.platform.qq_official import QQOfficialAdapter

    adapter = QQOfficialAdapter(
        app_id="your_app_id",
        app_secret="your_app_secret",
        is_sandbox=True,
        robot_id="your_robot_id",
    )
    adapter.start(on_event=event_handler)
"""

import asyncio
import logging
import time
from typing import Callable, List, Optional

from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg, LoyanText

from loyan.core.loyan_adapter.platform.qq_official.api import QQOfficialAPI
from loyan.core.loyan_adapter.platform.qq_official.gateway import QQOfficialGateway
from loyan.core.loyan_adapter.platform.qq_official.bind import MasterBinding
from loyan.core.loyan_adapter.platform.qq_official.sender import send_message

_logger = logging.getLogger("Adapter.QQOfficial")

# ── 调试埋点 ──
import urllib.request
_DEBUG_URL = "http://127.0.0.1:19809"
def _dbg(event: str, **kw):
    try:
        import json as _j
        data = _j.dumps({"event": event, **kw}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{_DEBUG_URL}/debug", data=data), timeout=0.5)
    except:
        pass


class QQOfficialAdapter(LoyanAdapter):
    """QQ 官方个人机器人适配器"""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        is_sandbox: bool = False,
        robot_id: str = "",
        config_path: str = "",
    ):
        self._app_id = app_id
        self._app_secret = app_secret
        self._is_sandbox = is_sandbox
        self._robot_id = robot_id
        self._config_path = config_path

        self._on_event: Optional[Callable[[LoyanEvent], None]] = None
        self._api = QQOfficialAPI(app_id, app_secret, is_sandbox)
        self._gateway: Optional[QQOfficialGateway] = None
        self._gateway_task: Optional[asyncio.Task] = None

        self._platform_info_cache: Optional[dict] = None
        self._platform_info_cache_time: float = 0
        self._binding = MasterBinding(config_path)

        # 被动回复状态
        self._last_msg_id: str = ""
        self._last_msg_id_time: float = 0.0

    # ── 生命周期 ──

    @property
    def is_connected(self) -> bool:
        gw = getattr(self, '_gateway', None)
        if gw:
            ws = getattr(gw, '_ws', None)
            if ws is not None and not getattr(ws, 'closed', True):
                return True
        return False

    async def start(self, on_event: Callable[[LoyanEvent], None]) -> None:
        self._binding._runtime = self._runtime
        self._binding.load_state()

        async def wrapped_event(event: LoyanEvent) -> None:
            _dbg("adapter_wrapped_event", sender_id=event.sender_id, chat_type=event.chat_type, raw_text=str(event.raw_text)[:50])
            self._last_msg_id = event.message_id or ""
            self._last_msg_id_time = time.time()
            if self._handle_bind_command_sync(event):
                _dbg("adapter_bind_captured")
                return
            _dbg("adapter_forward_to_framework")
            if on_event:
                await on_event(event)

        self._on_event = wrapped_event
        self._last_msg_id = ""
        self._last_msg_id_time = 0.0
        self._gateway = QQOfficialGateway(self._api, wrapped_event, self.tag)
        self._gateway_task = asyncio.ensure_future(self._gateway.start())

    async def stop(self) -> None:
        if self._gateway:
            await self._gateway.stop()
        if self._gateway_task and not self._gateway_task.done():
            self._gateway_task.cancel()
        await self._api.close()

    # ── 主从绑定 ──

    def _handle_bind_command_sync(self, event: LoyanEvent) -> bool:
        text = (event.raw_text or "").strip()
        if event.chat_type != "private" or text not in ("/master_set", "/unbind"):
            return False
        loop = asyncio.get_event_loop()
        loop.create_task(self._handle_bind_command(event))
        return True

    async def _handle_bind_command(self, event: LoyanEvent) -> bool:
        text = (event.raw_text or "").strip()
        sender_id = event.sender_id or ""
        chat_type = event.chat_type or "private"
        if chat_type != "private":
            return False

        async def _notify(msg: str):
            from loyan.core.loyan_adapter.send import loyan_send_msg
            await loyan_send_msg(sender_id, LoyanText(text=msg), chat_type=chat_type, tag=self.tag)

        if text == "/master_set":
            if self._binding.is_bound:
                await _notify(" 已经绑定了主人，无法再次绑定。如需更换请先输入 /unbind 解绑。")
                return True
            if self._binding.bind(sender_id):
                await _notify(" 主人绑定成功！您已被设为该机器人的主人。")
            return True

        if text == "/unbind":
            if not self._binding.is_bound:
                await _notify(" 当前未绑定主人，无需解绑。请输入 /master_set 进行绑定。")
                return True
            if self._binding.unbind(sender_id):
                await _notify(" 解绑成功！现在可以重新绑定新主人。")
            else:
                await _notify(" 只有当前绑定的主人才能解绑。")
            return True

        return False

    # ── 消息发送 ──

    async def send(self, target: str, segments: List[LoyanMsg], chat_type: str) -> bool:
        return await send_message(
            api=self._api,
            target=target,
            segments=segments,
            chat_type=chat_type,
            last_msg_id=self._last_msg_id,
            last_msg_id_time=self._last_msg_id_time,
            tag=self.tag,
        )

    # ── 平台信息 ──

    async def get_platform_info(self) -> dict:
        now = time.time()
        if self._platform_info_cache and (now - self._platform_info_cache_time) < 60:
            return self._platform_info_cache

        bot_info = await self._api.get_bot_info()
        result = {
            "friend_count": None,
            "group_count": None,
            "platform": "QQOfficial",
            "protocol_version": "v2",
        }
        if bot_info:
            result["protocol_version"] = f"v2 (bot: {bot_info.get('username', 'unknown')})"

        self._platform_info_cache = result
        self._platform_info_cache_time = now
        return result

    async def call_api(self, action: str, params: dict = None) -> Optional[dict]:
        return None

    def parse_business_event(self, raw: dict) -> Optional["BusinessEvent"]:
        """QQ 官方平台无业务事件（仅订阅消息意图），恒返回 None"""
        return None


# backward compatibility: 从 factory 导出 create_adapter
from .factory import create_adapter  # noqa: E402, F401
