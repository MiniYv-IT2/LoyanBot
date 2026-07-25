"""LoyanBot 适配器层 — 解耦插件与通信协议

提供:
- 消息段类型: LoyanText, LoyanImage, LoyanAt, LoyanReply, LoyanVoice, LoyanFile, LoyanVideo, LoyanForward
- 入站事件: LoyanEvent
- 适配器抽象: LoyanAdapter
- 统一入口: LoyanBot
"""

from loyan.core.loyan_adapter.message import (
    LoyanMsg,
    LoyanText,
    LoyanAt,
    LoyanImage,
    LoyanReply,
    LoyanVoice,
    LoyanFile,
    LoyanVideo,
    LoyanForward,
    loyan_text,
    loyan_image,
)
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.adapter import LoyanAdapter
from loyan.core.loyan_adapter.loyan_bot import LoyanBot

__all__ = [
    # 消息段
    "LoyanMsg", "LoyanText", "LoyanAt", "LoyanImage",
    "LoyanReply", "LoyanVoice", "LoyanFile", "LoyanVideo", "LoyanForward",
    "loyan_text", "loyan_image",
    # 事件 + 适配器
    "LoyanEvent", "LoyanAdapter",
    # 统一入口
    "LoyanBot",
]
