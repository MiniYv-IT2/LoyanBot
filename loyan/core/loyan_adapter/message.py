"""LoyanBot 统一消息段类型 — 插件与适配器之间的公共契约

插件只使用这些结构化类型，从不直接拼 CQ 码。
适配器负责将消息段翻译为平台原生格式。

设计原则：
- 每种消息段是一个轻量 dataclass，字段即语义
- 与平台无关，不做任何格式假设
- 未来新增消息段只需在此文件追加，无需修改适配层
"""

from dataclasses import dataclass, field
from typing import List, Union


@dataclass
class LoyanText:
    """纯文本消息段"""
    text: str


@dataclass
class LoyanAt:
    """@某人"""
    target_id: str


@dataclass
class LoyanImage:
    """图片消息段（三选一：本地路径 / 网络URL / 二进制数据）"""
    file_path: str = ""
    url: str = ""
    file_data: bytes = field(default_factory=bytes)


@dataclass
class LoyanReply:
    """回复引用某条消息"""
    message_id: str


@dataclass
class LoyanVoice:
    """语音消息段"""
    file_path: str = ""


@dataclass
class LoyanFile:
    """文件消息段"""
    file_path: str = ""
    url: str = ""


@dataclass
class LoyanVideo:
    """视频消息段"""
    file_path: str = ""
    url: str = ""
    file_data: bytes = field(default_factory=bytes)


@dataclass
class LoyanForward:
    """合并转发消息段"""
    forward_id: str = ""
    title: str = ""


# 联合类型：列表中每一元素为上述之一
LoyanMsg = Union[LoyanText, LoyanAt, LoyanImage, LoyanReply, LoyanVoice, LoyanFile, LoyanVideo, LoyanForward]


def loyan_text(text: str) -> LoyanText:
    """快捷构造纯文本段"""
    return LoyanText(text=text)


def loyan_image(file_path: str = "", url: str = "") -> LoyanImage:
    """快捷构造图片段"""
    return LoyanImage(file_path=file_path, url=url)
