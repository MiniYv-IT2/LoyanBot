"""LoyanBot 统一入口 — 插件通过此类发送消息，与适配器解耦

用法:
    from loyan.core.loyan_adapter.loyan_bot import LoyanBot

    bot = LoyanBot(adapter)
    bot.send(target, LoyanText("你好"), LoyanImage(file_path="/tmp/1.png"), chat_type="group")
"""

from typing import List

from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.message import LoyanMsg, LoyanText, loyan_text


class LoyanBot:
    """LoyanBot 统一入口

    上层（插件、handler）通过 LoyanBot.send() 发送消息，
    无需关心底层是 OneBot HTTP 还是 WebSocket。
    """

    def __init__(self, adapter: LoyanAdapter):
        self._adapter = adapter

    def send(self, target: str, *segments: LoyanMsg, chat_type: str = "private") -> bool:
        """发送消息

        支持多种调用方式：
            bot.send(target, LoyanText("你好"), chat_type="group")
            bot.send(target, LoyanImage(file_path="/tmp/1.png"))
        """
        seg_list: List[LoyanMsg] = list(segments)
        return self._adapter.send(target, seg_list, chat_type)

    def reply_text(self, event: "LoyanEvent", text: str) -> bool:
        """快捷文本回复（自动匹配目标）"""
        return self.send(event.target_id, loyan_text(text), chat_type=event.chat_type)

    def _get_adapter(self) -> LoyanAdapter:
        """（内部）获取底层适配器"""
        return self._adapter
