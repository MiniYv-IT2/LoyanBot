"""Satori 适配器 — 基于 satori-python-client 的多平台接入

支持平台：QQ（通过 NapCat+Koishi）、Telegram、Discord、飞书（Lark）、微信（WeChat/WeCom）、钉钉（DingTalk）、Kook、Minecraft 等（通过 Satori 协议）

实现 LoyanAdapter 抽象类，整合 satori-python-client：
- App: Satori 客户端连接管理
- event: 事件转换（Satori Event → LoyanEvent）
- message: 消息转换

用法:
    from loyan.core.loyan_adapter.platform.satori import SatoriAdapter

    adapter = SatoriAdapter(host="127.0.0.1", port=5140, token="your-token")
    adapter.start(on_event=event_handler)
"""

import asyncio
import json
import logging
import os
from typing import Callable, List, Optional

from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg, LoyanText

_logger = logging.getLogger("Adapter.Satori")


async def _publish_business(biz) -> None:
    """发布业务事件到 EventBus（总线未就绪时静默跳过）"""
    try:
        from loyan.core.event import event_bus
        publish = getattr(event_bus, "publish_business", None)
        if publish is not None:
            await publish(biz)
    except Exception:
        pass


class SatoriAdapter(LoyanAdapter):
    """Satori 协议适配器（基于 satori-python-client）"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5140,
        token: str = "",
        path: str = "",
        config: dict = None,
    ):
        self._host = host
        self._port = port
        self._token = token
        self._path = path
        self._config = config or {}

        self._on_event: Optional[Callable[[LoyanEvent], None]] = None
        self._app = None
        self._account = None
        self._self_id: str = ""
        self._self_name: str = ""
        self._login_cache: dict = {}
        self._platform_info_cache: Optional[dict] = None
        self._platform_info_cache_time: float = 0
        self._task: Optional[asyncio.Task] = None
        self._ready: asyncio.Event = asyncio.Event()
        self._pending_messages: list = []  # 未连接时暂存的消息

    # ── 生命周期 ──

    async def start(self, on_event: Callable[[LoyanEvent], None]) -> None:
        self._on_event = on_event
        self._task = asyncio.ensure_future(self._async_start())

    async def _async_start(self):
        from satori.client import App, WebsocketsInfo

        self._app = App(
            WebsocketsInfo(
                host=self._host,
                port=self._port,
                path=self._path,
                token=self._token or None,
            )
        )

        adapter_self = self

        async def _on_account_update(account, state):
            """账号状态更新回调"""
            adapter_self._account = account
            if hasattr(account, 'self_id'):
                adapter_self._self_id = str(account.self_id)
            try:
                login = await account.protocol.login_get()
                if login and login.user:
                    adapter_self._login_cache = {
                        "user_id": str(login.user.id),
                        "nickname": login.user.name or login.user.nick or "",
                        "avatar_url": login.user.avatar or "",
                    }
                try:
                    friends = await account.protocol.call_api("friend.list", {})
                    if isinstance(friends, dict) and "data" in friends:
                        adapter_self._login_cache["friend_count"] = len(friends["data"])
                except Exception:
                    pass
                try:
                    guilds = await account.protocol.call_api("guild.list", {})
                    if isinstance(guilds, dict) and "data" in guilds:
                        adapter_self._login_cache["group_count"] = len(guilds["data"])
                except Exception:
                    pass
            except Exception:
                pass
            if not adapter_self._ready.is_set():
                adapter_self._ready.set()
                _logger.info(f"Satori 连接就绪，account: {account}, state: {state}")
                # 补发暂存消息（OneBot 同款逻辑）
                if adapter_self._pending_messages:
                    pending = adapter_self._pending_messages[:]
                    adapter_self._pending_messages.clear()
                    for target, segments, chat_type in pending:
                        try:
                            await adapter_self.send(target, segments, chat_type)
                        except Exception as e:
                            _logger.error(f"[Satori] 补发失败: {e}")

        self._app.lifecycle_callbacks.append(_on_account_update)

        @self._app.register
        async def _handle_event(account, event):
            """Satori 事件回调 → LoyanEvent"""
            adapter_self._account = account
            if not adapter_self._ready.is_set():
                adapter_self._ready.set()
            _logger.debug(f"received event: type={event.type}")
            try:
                loyan_event = _satori_event_to_loyan(event, adapter_self.tag)
                if loyan_event and adapter_self._on_event:
                    _logger.debug(f"event converted: {loyan_event.raw_text}")
                    await adapter_self._on_event(loyan_event)
                else:
                    # 非消息事件 → 业务事件转换并发布
                    biz = adapter_self.parse_business_event(event)
                    if biz is not None:
                        await _publish_business(biz)
            except Exception as e:
                _logger.error(f"Satori 事件转换异常: {e}", exc_info=True)

        await self._app.run_async()

    async def stop(self) -> None:
        self._pending_messages.clear()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        if self._app:
            await self._app.shutdown()

    # ── 消息发送 ──

    async def send(self, target: str, segments: List[LoyanMsg], chat_type: str) -> bool:
        """发送消息到指定目标

        Args:
            target: 目标 ID（用户QQ号或群号）
            segments: LoyanMsg 消息段列表
            chat_type: "private" | "group"
        """
        if not segments:
            return False



        # 未连接时暂存（OneBot 同款逻辑）
        if not self._ready.is_set() or not self._account:
            self._pending_messages.append((target, segments, chat_type))
            return False

        try:
            from satori.element import Image, Audio, File, Video, At
            from loyan.core.loyan_adapter.message import LoyanText, LoyanImage, LoyanVoice, LoyanFile, LoyanForward, LoyanAt as LoyanAtMsg

            elements = []
            for seg in segments:
                if isinstance(seg, LoyanText):
                    if seg.text:
                        elements.append(seg.text)
                elif isinstance(seg, LoyanImage):
                    url = seg.url or seg.file_path
                    if url:
                        if url.startswith(("http://", "https://", "data:")):
                            elements.append(Image(src=url))
                        else:
                            from loyan.core.loyan_adapter.platform.satori.message import _file_to_data_url
                            data_url = _file_to_data_url(url)
                            if data_url:
                                elements.append(Image(src=data_url))
                elif isinstance(seg, LoyanVoice):
                    if seg.file_path:
                        if seg.file_path.startswith(("http://", "https://", "data:")):
                            elements.append(Audio(src=seg.file_path))
                        else:
                            elements.append(Audio.of(path=seg.file_path))
                elif isinstance(seg, LoyanFile):
                    url = seg.url or seg.file_path
                    if url:
                        if url.startswith(("http://", "https://", "data:")):
                            elements.append(File(src=url))
                        else:
                            elements.append(File.of(path=url))
                elif isinstance(seg, LoyanVideo):
                    url = seg.url or seg.file_path
                    if url:
                        if url.startswith(("http://", "https://", "data:")):
                            elements.append(Video(src=url))
                        else:
                            elements.append(Video.of(path=url))
                elif isinstance(seg, LoyanAtMsg):
                    elements.append(At(id=seg.target_id))

            if not elements:
                return False

            if target.startswith("private:") or target.startswith("group:"):
                channel_id = target
            elif chat_type == "private":
                channel_id = f"private:{target}"
            else:
                channel_id = target
            try:
                await asyncio.wait_for(
                    self._account.protocol.send_message(
                        channel=channel_id,
                        message=elements,
                    ),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                _logger.error(f"发送超时(15s): {chat_type} -> {target}")
                return False
            _logger.info(f"消息发送成功: {chat_type} -> {target}")
            return True
        except Exception as e:
            _logger.error(f"发送异常: {e}", exc_info=True)
            return False

    # ── 平台信息 ──

    async def get_platform_info(self) -> dict:
        import time
        now = time.time()
        if self._platform_info_cache and (now - self._platform_info_cache_time) < 60:
            return self._platform_info_cache

        result = {
            "friend_count": None,
            "group_count": None,
            "platform": "Satori",
            "protocol_version": "1.0",
            "user_id": None,
            "nickname": None,
        }

        if self._login_cache:
            result.update(self._login_cache)

        self._platform_info_cache = result
        self._platform_info_cache_time = now
        return result

    # ── 工厂函数 ──

    def parse_business_event(self, raw) -> Optional["BusinessEvent"]:
        """Satori 事件 → BusinessEvent（委托 event.py，支持 dict/Event 对象）"""
        from loyan.core.loyan_adapter.platform.satori.event import satori_event_to_business
        return satori_event_to_business(raw)

    @staticmethod
    def create_adapter(config: dict) -> "SatoriAdapter":
        """根据配置创建 SatoriAdapter 实例"""
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 5140)
        token = config.get("token", "")
        path = config.get("path", "")

        adapter = SatoriAdapter(
            host=host,
            port=port,
            token=token,
            path=path,
            config=config,
        )
        adapter.conn_type_display = "WebSocket"
        return adapter


def create_adapter(config: dict) -> "SatoriAdapter":
    """模块级工厂函数，供 main.py 动态加载调用"""
    return SatoriAdapter.create_adapter(config)


def _satori_event_to_loyan(event, tag: IdentityTag) -> Optional[LoyanEvent]:
    """将 satori-python 的 Event 转换为 LoyanEvent"""
    from satori.model import ChannelType
    from loyan.core.loyan_adapter.message import LoyanAt

    # 只处理消息创建事件（Satori 协议用连字符）
    if event.type != "message-created":
        return None

    # 提取消息数据
    message = event.message
    if not message:
        return None

    user = event.user
    if not user:
        return None

    sender_id = str(user.id) if user.id else ""
    nickname = user.name or ""

    if not sender_id:
        return None

    self_id = ""
    for src in ("login", "self", "account"):
        obj = getattr(event, src, None)
        if obj:
            uid = getattr(obj, "user_id", None) or getattr(getattr(obj, "user", None), "id", None)
            if uid:
                self_id = str(uid)
                break

    if self_id and sender_id == self_id:
        return None

    channel = event.channel
    guild = getattr(event, 'guild', None)

    if channel and hasattr(channel, 'type'):
        chat_type = "private" if channel.type == ChannelType.DIRECT else "group"
    else:
        chat_type = "private"

    if chat_type == "private":
        target_id = str(channel.id) if channel else ""
    else:
        target_id = str(guild.id) if guild else (str(channel.id) if channel else "")


    from loyan.core.loyan_adapter.platform.satori.message import satori_to_loyan, extract_plain_text
    elements = getattr(message, 'message', None) or message.content
    segments = satori_to_loyan(elements)
    raw_text = extract_plain_text(segments).strip()

    message_id = str(message.id) if message.id else ""

    # 检测 @机器人
    is_at_bot = any(
        seg.target_id == self_id
        for seg in segments
        if isinstance(seg, LoyanAt)
    ) if self_id else False

    raw_data = {"satori_event": event} if hasattr(event, '__dict__') else {}
    if chat_type == "group" and guild:
        raw_data["group_id"] = guild.id

    return LoyanEvent(
        sender_id=sender_id,
        target_id=target_id or sender_id,
        chat_type=chat_type,
        segments=segments,
        raw_text=raw_text,
        message_id=message_id,
        nickname=nickname,
        is_at_bot=is_at_bot,
        raw_data=raw_data,
        source=tag,
    )
