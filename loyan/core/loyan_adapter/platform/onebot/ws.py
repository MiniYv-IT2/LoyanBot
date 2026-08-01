"""OneBot WebSocket 适配器 — 遵循 OneBot 11 标准

支持两种模式（统一使用 websockets 异步库）：
- 正向 WS（forward）：主动连接 OneBot 的 /ws 端点
- 反向 WS（reverse）：监听端口，等待 OneBot 客户端连接

依赖: pip install websockets

OneBot 11 标准 JSON 格式：
  入站: {"action": "send_msg", "params": {...}}
  出站: {"post_type": "message", ...}（与 HTTP 回调格式一致）

用法:
    # 正向
    adapter = LoyanOneBotWS(mode="forward", host="127.0.0.1", port=3001)

    # 反向
    adapter = LoyanOneBotWS(mode="reverse", host="0.0.0.0", port=8080)
"""

import asyncio
import json
import logging
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

import websockets
import websockets.asyncio.client
import websockets.asyncio.server

from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.message import LoyanMsg
from loyan.core.loyan_adapter.platform.onebot.cq import loyan_to_cq, cq_to_loyan

# 压掉 websockets 库自身的 INFO 日志（重复输出监听信息）
logging.getLogger("websockets").setLevel(logging.WARNING)


class LoyanOneBotWS(LoyanAdapter):
    """OneBot 11 WebSocket 适配器

    Args:
        mode: "forward"（主动连接）或 "reverse"（被动监听）
        host: 正向=OneBot 地址, 反向=监听地址
        port: 正向=OneBot WS 端口, 反向=监听端口
        access_token: OneBot access_token（可选）
        robot_id: 机器人 ID（用于 @检测）
    """

    def __init__(
        self,
        mode: str = "forward",
        host: str = "127.0.0.1",
        port: int = 3001,
        access_token: str = "",
        robot_id: str = "",
    ):
        if mode not in ("forward", "reverse"):
            raise ValueError(f"mode 必须为 'forward' 或 'reverse'，收到: {mode}")
        self._mode = mode
        self._host = host
        self._port = port
        self._access_token = access_token
        self._robot_id = robot_id
        self._on_event: Callable[[LoyanEvent], None] | None = None
        self._running = False
        self._ws = None
        self._task: asyncio.Task | None = None
        self._api_lock = asyncio.Lock()
        self._api_event = asyncio.Event()
        self._api_responses: dict = {}
        self._api_send_queue: asyncio.Queue = asyncio.Queue()
        self._pending_messages: list = []
        self._event_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ws_event_")
        self._logger = logging.getLogger("Adapter.OneBot.ws")
        # 平台信息缓存，避免高频 API 调用刷屏日志
        self._platform_info_cache: dict | None = None
        self._platform_info_cache_time: float = 0.0
        self._platform_cache_lock = threading.Lock()  # 防多线程竞态重复更新

    # ── 出站：发送消息 ──

    async def send(self, target: str, segments: List[LoyanMsg], chat_type: str) -> bool:
        cq_str = loyan_to_cq(segments)
        if not cq_str:
            self._logger.warning("[OneBotWS] 消息段列表为空")
            return False
        try:
            action_data = {
                "action": "send_msg",
                "params": {
                    "message_type": chat_type,
                    "user_id" if chat_type == "private" else "group_id": int(target),
                    "message": cq_str,
                },
                "echo": f"loyan_{int(time.time() * 1000)}",
            }
        except (ValueError, TypeError) as e:
            self._logger.error(f"[OneBotWS] 构造 send_msg 失败: target={target}, chat_type={chat_type}, err={e}")
            return False
        return await self._ws_send_async(action_data)

    async def call_api(self, action: str, params: dict = None, timeout: float = 5.0) -> Optional[dict]:
        async with self._api_lock:
            return await self._call_api_impl_async(action, params, timeout)

    async def _call_api_impl_async(self, action: str, params: dict, timeout: float) -> Optional[dict]:
        import time
        if not self._ws:
            self._logger.warning(f"[OneBotWS] call_api('{action}') 失败: 未连接")
            return None

        echo_id = f"loyan_api_{int(time.time() * 1000)}"
        t_api = time.time()
        action_data = {
            "action": action,
            "params": params or {},
            "echo": echo_id,
        }

        await self._api_send_queue.put(action_data)
        self._api_event.set()

        self._api_event.clear()
        try:
            await asyncio.wait_for(
                self._wait_for_api_response(echo_id),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self._logger.warning(f"[OneBotWS] call_api('{action}') 超时 耗时{time.time()-t_api:.1f}s: 未收到 echo={echo_id} 的响应")
            return None

        data = self._api_responses.pop(echo_id, None)
        if data and data.get("status") == "ok":
            return data.get("data", {})
        self._logger.warning(
            f"[OneBotWS] API '{action}' 返回失败: "
            f"retcode={data.get('retcode') if data else '?'}, msg={data.get('msg', '')}"
        )
        return None

    async def _wait_for_api_response(self, echo_id: str) -> None:
        while echo_id not in self._api_responses:
            await asyncio.sleep(0.05)

    async def get_platform_info(self) -> dict:
        import time
        now = time.time()
        # 快速路径：缓存有效则直接返回（无锁）
        if self._platform_info_cache is not None and (now - self._platform_info_cache_time) < 60:
            return self._platform_info_cache

        with self._platform_cache_lock:
            if self._platform_info_cache is not None and (time.time() - self._platform_info_cache_time) < 60:
                return self._platform_info_cache

            t_api = time.time()
            result = {
                "friend_count": None,
                "group_count": None,
                "platform": "OneBot",
                "protocol_version": None,
                "nickname": None,
            }
            try:
                with ThreadPoolExecutor(max_workers=4) as ex:
                    fut_friends = ex.submit(self.call_api, "get_friend_list")
                    fut_groups = ex.submit(self.call_api, "get_group_list")
                    fut_version = ex.submit(self.call_api, "get_version_info")
                    fut_login = ex.submit(self.call_api, "get_login_info")
                    friend_list = fut_friends.result(timeout=5)
                    group_list = fut_groups.result(timeout=5)
                    version_info = fut_version.result(timeout=5)
                    login_info = fut_login.result(timeout=5)
                if isinstance(friend_list, list):
                    result["friend_count"] = len(friend_list)
                if isinstance(group_list, list):
                    result["group_count"] = len(group_list)
                if isinstance(version_info, dict):
                    app_name = version_info.get("app_name", "")
                    app_ver = version_info.get("app_version", "")
                    result["protocol_version"] = f"{app_name} {app_ver}".strip()
                if isinstance(login_info, dict):
                    result["nickname"] = login_info.get("nickname", "")
            except Exception as e:
                self._logger.error(f"[OneBotWS] get_platform_info 失败: {type(e).__name__}: {e}")
            self._platform_info_cache = result
            self._platform_info_cache_time = time.time()
            return result

    # ── 入站：解析 OneBot JSON → LoyanEvent ──

    def _parse_ws_message(self, data: dict) -> Optional[LoyanEvent]:
        """将 OneBot WS 消息解析为 LoyanEvent"""
        post_type = data.get("post_type", "")
        if post_type == "meta_event":
            return None
        if post_type not in ("message", "notice"):
            return None
        # 过滤输入状态通知（对方正在输入...），避免产生空消息日志
        if data.get("notice_type") == "notify" and data.get("sub_type") == "input_status":
            return None
        # 点赞通知不是消息，没有内容可处理
        if data.get("notice_type") == "like":
            return None

        chat_type = data.get("message_type", "private")
        sender_id = str(data.get("user_id", ""))
        # 过滤机器人自己的消息（sub_type=self 或 userId==selfId 或 userId==robotId）
        if data.get("sub_type") == "self":
            return None
        self_id = str(data.get("self_id", ""))
        if self_id and sender_id == self_id:
            return None
        if self._robot_id and sender_id == self._robot_id:
            return None
        target_id = str(
            data.get("user_id", "") if chat_type == "private" else data.get("group_id", "")
        )
        raw_message = data.get("raw_message", "")
        # 自回显：OneBot 推送已发送消息时 raw_message 为空，直接丢弃
        if not raw_message.strip():
            return None
        nickname = ""
        if isinstance(data.get("sender"), dict):
            nickname = data["sender"].get("nickname", "")

        segments = cq_to_loyan(raw_message)

        raw_text = ""
        for seg in segments:
            from loyan.core.loyan_adapter.message import LoyanText, LoyanImage, LoyanAt, LoyanReply, LoyanVoice, LoyanFile
            if isinstance(seg, LoyanText):
                raw_text += seg.text
            elif isinstance(seg, LoyanImage):
                raw_text += "[图片]"
            elif isinstance(seg, LoyanAt):
                raw_text += f"[@{seg.target_id}]"
            elif isinstance(seg, LoyanReply):
                raw_text += "[回复]"
            elif isinstance(seg, LoyanVoice):
                raw_text += "[语音]"
            elif isinstance(seg, LoyanFile):
                name = seg.file_path.split("/")[-1].split("\\")[-1] if seg.file_path else ""
                raw_text += f"[文件:{name}]" if name else "[文件]"

        is_at_bot = False
        if chat_type == "group" and self._robot_id:
            for seg in segments:
                from loyan.core.loyan_adapter.message import LoyanAt
                if isinstance(seg, LoyanAt) and seg.target_id == self._robot_id:
                    is_at_bot = True
                    break

        return LoyanEvent(
            sender_id=sender_id,
            target_id=target_id,
            chat_type=chat_type,
            segments=segments,
            raw_text=raw_text,
            message_id=str(data.get("message_id", "")),
            nickname=nickname,
            is_at_bot=is_at_bot,
            raw_data=data,
        )

    def parse_business_event(self, raw: dict) -> Optional["BusinessEvent"]:
        """OneBot notice 事件 → BusinessEvent（委托 business.py）"""
        from loyan.core.loyan_adapter.platform.onebot.business import parse_onebot_business
        return parse_onebot_business(raw)

    # ── 生命周期 ──

    async def start(self, on_event: Callable[[LoyanEvent], None]) -> None:
        self._on_event = on_event
        self._running = True
        if self._mode == "forward":
            self._task = asyncio.ensure_future(self._forward_connect())
        else:
            self._task = asyncio.ensure_future(self._reverse_listen())
        self._logger.info(f"[OneBotWS] {self._mode} 模式已启动 {self._host}:{self._port}")

    async def stop(self) -> None:
        self._running = False
        self._pending_messages.clear()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None


    async def _close_ws(self) -> None:
        """优雅关闭 WS 连接"""
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _handle_connection(self, ws, label: str = "") -> None:
        """连接建立后的统一处理：补发暂存消息 → 收发循环

        正反向复用，消除重复代码。
        """
        self._ws = ws
        if label:
            self._logger.info(f"[OneBotWS] {label}")
        # 补发未连接时暂存的消息
        if self._pending_messages:
            self._logger.info(f"[OneBotWS] 补发 {len(self._pending_messages)} 条暂存消息")
            for data in self._pending_messages:
                try:
                    await ws.send(json.dumps(data, ensure_ascii=False))
                except Exception as e:
                    self._logger.error(f"[OneBotWS] 补发失败: {e}")
            self._pending_messages.clear()
        # 进入收发循环，直到连接断开
        await self._recv_loop(ws)
        self._ws = None



    # ── 内部：正向连接 ──

    # ╔══════════════════════════════════════════════════════════════╗
    # ║ 架构约束（禁止违反，否则导致 call_api 死锁/超时）         ║
    # ║ 1. recv_loop 是本线程唯一 WS 收发者，绝不可阻塞          ║
    # ║ 2. 事件处理必须用 _event_executor.submit() 异步派发      ║
    # ║ 3. 其他线程发 API 请求必须走 _api_send_queue 队列        ║
    # ║ 4. API 响应通过 _api_condition 条件变量路由              ║
    # ╚══════════════════════════════════════════════════════════════╝

    async def _forward_connect(self) -> None:
        """主动连接 OneBot WS 端点，断线自动重连"""
        ws_url = f"ws://{self._host}:{self._port}"
        if self._access_token:
            ws_url += f"?access_token={self._access_token}"

        while self._running:
            try:
                async for ws in websockets.asyncio.client.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=1,
                ):
                    await self._handle_connection(ws, f"正向连接成功: {ws_url}")
            except Exception as e:
                self._logger.error(f"[OneBotWS] 正向连接失败: {type(e).__name__}: {e}")

            # 断线重连
            if self._running:
                self._logger.info("[OneBotWS] 5秒后重连...")
                await asyncio.sleep(5)

    # ── 内部：反向监听 ──

    async def _reverse_listen(self) -> None:
        """监听端口，等待 OneBot 客户端连接"""
        self._logger.info(f"[OneBotWS] 反向监听 {self._host}:{self._port}")

        async def on_connect(ws):
            """每次有新客户端连入时回调"""
            addr = ws.remote_address
            await self._handle_connection(ws, f"反向连接接入: {addr}")

        server = await websockets.asyncio.server.serve(
            on_connect, self._host, self._port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=1,
        )

        # 保持 server 存活，直到停止
        while self._running:
            await asyncio.sleep(1)

        server.close()
        await server.wait_closed()

    # ── 内部：共享收发循环 ──

    async def _recv_loop(self, ws) -> None:
        """共享的接收循环（正反向通用）

        使用 asyncio.wait 双监听：
        - ws.recv()：接收 OneBot 推送的消息/API 响应
        - _api_event：call_api 入队后触发，立即唤醒 drain 队列
        """
        _cycle = 0
        while self._running:
            _cycle += 1
            #  消费 worker 线程入队的 API 请求（由本线程发送）
            await self._drain_api_send_queue_async(ws)

            # 双监听：recv 或 队列事件（入队即唤醒）
            self._api_event.clear()
            recv_task = asyncio.create_task(ws.recv())
            event_task = asyncio.create_task(self._api_event.wait())

            done, pending = await asyncio.wait(
                [recv_task, event_task],
                timeout=0.5,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if recv_task not in done:
                continue

            try:
                raw = recv_task.result()
            except websockets.ConnectionClosed as e:
                self._logger.warning(f"[OneBotWS] 远端关闭连接: {e}")
                break

            if not isinstance(raw, str):
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                self._logger.warning(f"[OneBotWS] JSON 解析失败: {e} | raw={raw[:200]}")
                continue

            status_val = data.get("status")
            if isinstance(status_val, str) and "echo" in data:
                echo = data.get("echo", "")
                self._api_responses[echo] = data
                self._api_event.set()
                continue

            event = self._parse_ws_message(data)
            if event:
                try:
                    from loyan.core.event import event_bus
                    await event_bus.publish(event)
                except Exception as e:
                    self._logger.error(f"[OneBotWS] EventBus 派发失败: {e}")
            else:
                # 非消息事件 → 业务事件转换并发布
                try:
                    biz = self.parse_business_event(data)
                    if biz is not None:
                        from loyan.core.event import event_bus
                        publish = getattr(event_bus, "publish_business", None)
                        if publish is not None:
                            await publish(biz)
                except Exception as e:
                    self._logger.error(f"[OneBotWS] 业务事件发布失败: {e}")

    async def _drain_api_send_queue_async(self, ws) -> None:
        """消费 worker 线程入队的 API 请求（异步版，recv_loop 内调用）"""
        while not self._api_send_queue.empty():
            action_data = self._api_send_queue.get_nowait()
            try:
                await ws.send(json.dumps(action_data, ensure_ascii=False))
            except websockets.ConnectionClosed:
                # 连接断开时把请求放回队列，下次重连后重试
                self._api_send_queue.put(action_data)
                break

    # ── 内部辅助 ──

    async def _ws_send_async(self, data: dict) -> bool:
        if not self._ws:
            if self._running:
                self._pending_messages.append(data)
                count = len(self._pending_messages)
                self._logger.info(f"[OneBotWS] 未连接，消息暂存（共{count}条）")
                return False
            self._logger.warning("[OneBotWS] 未连接且已停止，无法发送")
            return False
        try:
            payload = json.dumps(data, ensure_ascii=False)
            await self._ws.send(payload)
            return True
        except Exception as e:
            self._logger.error(f"[OneBotWS] 发送失败: {e}")
            return False