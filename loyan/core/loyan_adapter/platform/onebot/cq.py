"""CQ 码 ↔ LoyanMsg 双向转换（OneBot 平台专属）

全框架唯一一处构造和解析 CQ 码的地方。
其他平台（Discord/Telegram）不依赖此模块。

遵循 OneBot 11 标准 CQ 码格式：[CQ:type,key1=value1,key2=value2,...]
"""

import re
from typing import List

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
)

# CQ 码正则：[CQ:type,key=val,...]
_CQ_PATTERN = re.compile(r"\[CQ:(\w+),([^\]]*)\]")


# ──────────────────── 出站：LoyanMsg → CQ 码字符串 ────────────────────

def loyan_to_cq(segments: List[LoyanMsg]) -> str:
    """LoyanMsg 列表 → CQ 码字符串（发送消息时调用）"""
    parts: List[str] = []
    for seg in segments:
        if isinstance(seg, LoyanText):
            parts.append(seg.text)
        elif isinstance(seg, LoyanAt):
            parts.append(f"[CQ:at,qq={seg.target_id}]")
        elif isinstance(seg, LoyanImage):
            if seg.file_path:
                parts.append(f"[CQ:image,file=file://{seg.file_path}]")
            elif seg.url:
                parts.append(f"[CQ:image,url={seg.url}]")
            elif seg.file_data:
                import base64
                b64 = base64.b64encode(seg.file_data).decode()
                parts.append(f"[CQ:image,file=base64://{b64}]")
        elif isinstance(seg, LoyanReply):
            parts.append(f"[CQ:reply,id={seg.message_id}]")
        elif isinstance(seg, LoyanVoice):
            if seg.file_path:
                parts.append(f"[CQ:record,file=file://{seg.file_path}]")
        elif isinstance(seg, LoyanFile):
            if seg.file_path:
                parts.append(f"[CQ:file,file=file://{seg.file_path}]")
            elif seg.url:
                parts.append(f"[CQ:file,url={seg.url}]")
        elif isinstance(seg, LoyanVideo):
            if seg.file_path:
                parts.append(f"[CQ:video,file=file://{seg.file_path}]")
            elif seg.url:
                parts.append(f"[CQ:video,url={seg.url}]")
            elif seg.file_data:
                import base64
                b64 = base64.b64encode(seg.file_data).decode()
                parts.append(f"[CQ:video,file=base64://{b64}]")
        elif isinstance(seg, LoyanForward):
            parts.append(f"[CQ:forward,id={seg.forward_id}]")
        elif isinstance(seg, str):
            # 兼容旧插件直接传字符串的写法
            parts.append(seg)
    return "".join(parts)


# ──────────────────── 入站：CQ 码字符串 → LoyanMsg 列表 ────────────────────

def cq_to_loyan(raw_message: str) -> List[LoyanMsg]:
    """CQ 码字符串 → LoyanMsg 列表（收到消息时调用）

    解析失败或未知 CQ 类型回退为 LoyanText。
    """
    segments: List[LoyanMsg] = []
    last_end = 0

    for m in _CQ_PATTERN.finditer(raw_message):
        # 匹配前的纯文本
        if m.start() > last_end:
            text = raw_message[last_end:m.start()]
            if text:
                segments.append(LoyanText(text=text))

        cq_type = m.group(1)
        params_str = m.group(2)

        # 解析 key=value 对
        params: dict = {}
        for pair in params_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k.strip()] = v.strip()

        segment = _cq_to_segment(cq_type, params)
        if segment is not None:
            segments.append(segment)

        last_end = m.end()

    # 末尾残余文本
    if last_end < len(raw_message):
        text = raw_message[last_end:]
        if text:
            segments.append(LoyanText(text=text))

    # 若没有解析出任何段，整条就是纯文本
    if not segments:
        segments.append(LoyanText(text=raw_message))

    return segments


def _cq_to_segment(cq_type: str, params: dict) -> LoyanMsg | None:
    """单个 CQ 码 → 对应 LoyanMsg"""
    if cq_type == "at":
        return LoyanAt(target_id=params.get("qq", ""))
    elif cq_type == "image":
        file = params.get("file", "")
        if file.startswith("file://"):
            return LoyanImage(file_path=file[7:])
        elif file.startswith("http"):
            return LoyanImage(url=file)
        else:
            return LoyanImage(url=file)
    elif cq_type == "reply":
        return LoyanReply(message_id=params.get("id", ""))
    elif cq_type == "record":
        return LoyanVoice(file_path=params.get("file", ""))
    elif cq_type == "file":
        return LoyanFile(file_path=params.get("file", ""))
    elif cq_type == "video":
        file = params.get("file", "")
        if file.startswith("file://"):
            return LoyanVideo(file_path=file[7:])
        elif file.startswith("http"):
            return LoyanVideo(url=file)
        else:
            return LoyanVideo(url=file)
    elif cq_type == "forward":
        return LoyanForward(forward_id=params.get("id", ""))
    # 未知/未实现的 CQ 类型 → 替换为可读文本
    _CQ_DISPLAY = {
        "json": "[JSON卡片]",
        "markdown": "[卡片消息]",
        "forward": "[合并转发]",
        "poke": "[戳一戳]",
        "dice": "[骰子]",
        "rps": "[猜拳]",
        "contact": "[推荐好友]",
        "share": "[链接分享]",
    }
    display = _CQ_DISPLAY.get(cq_type, f"[{cq_type}]")
    return LoyanText(text=display)
