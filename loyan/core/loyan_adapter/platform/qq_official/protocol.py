"""QQ 官方协议转换 — 官方 Payload ↔ LoyanEvent/LoyanMsg

职责：
- parse_event: 将 QQ 官方 WebSocket 事件解析为 LoyanEvent
- build_segments: 将 LoyanMsg 列表转换为 QQ 官方消息格式
- build_payload: 构建发送消息的 HTTP 请求体

参考文档：https://bot.q.qq.com/wiki/develop/api-v2/
"""

import logging
from typing import List, Optional

from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
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

_logger = logging.getLogger("Adapter.QQOfficial.protocol")

# ── 调试埋点 ──
import urllib.request
import json as _json
_DEBUG_URL = "http://127.0.0.1:19809"
def _dbg(event: str, **kw):
    try:
        data = _json.dumps({"event": event, **kw}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{_DEBUG_URL}/debug", data=data), timeout=0.5)
    except:
        pass


# ============================================================
# 入站：QQ 官方事件 → LoyanEvent
# ============================================================

def parse_event(raw: dict, source: Optional[IdentityTag] = None) -> Optional[LoyanEvent]:
    """将 QQ 官方 WebSocket 事件解析为 LoyanEvent"""
    event_type = raw.get("type", "")
    _dbg("protocol_entry", event_type=event_type, has_source=source is not None, raw_keys=list(raw.keys()))

    # 消息事件
    if event_type == "C2C_MESSAGE_CREATE":
        return _parse_c2c_message(raw, source)
    elif event_type == "GROUP_AT_MESSAGE_CREATE":
        return _parse_group_message(raw, source)
    elif event_type == "DIRECT_MESSAGE_CREATE":
        return _parse_direct_message(raw, source)

    # 其他事件暂不处理
    _dbg("protocol_ignored", event_type=event_type)
    return None


def _parse_c2c_message(raw: dict, source: Optional[IdentityTag]) -> LoyanEvent:
    """解析单聊消息（消息列表）"""
    data = raw.get("data", raw)
    author = data.get("author", {})
    content = data.get("content", "")

    sender_id = author.get("user_openid", "")
    message_id = data.get("id", "")
    nickname = author.get("username", "")

    segments = _parse_message_content(content, data)
    raw_text = _extract_plain_text(segments).strip()

    return LoyanEvent(
        sender_id=sender_id,
        target_id=sender_id,  # 单聊 target = sender
        chat_type="private",
        segments=segments,
        raw_text=raw_text,
        message_id=message_id,
        nickname=nickname,
        is_at_bot=False,
        raw_data=data,
        source=source,
    )


def _parse_group_message(raw: dict, source: Optional[IdentityTag]) -> LoyanEvent:
    """解析群聊 @消息"""
    data = raw.get("data", raw)
    author = data.get("author", {})
    content = data.get("content", "")

    sender_id = author.get("member_openid", "")
    group_openid = data.get("group_openid", "")
    message_id = data.get("id", "")
    nickname = author.get("username", "")

    segments = _parse_message_content(content, data)
    raw_text = _extract_plain_text(segments).strip()

    return LoyanEvent(
        sender_id=sender_id,
        target_id=group_openid,
        chat_type="group",
        segments=segments,
        raw_text=raw_text,
        message_id=message_id,
        nickname=nickname,
        is_at_bot=True,  # 群聊只有 @机器人 才会触发
        raw_data=data,
        source=source,
    )


def _parse_direct_message(raw: dict, source: Optional[IdentityTag]) -> LoyanEvent:
    """解析频道私信"""
    data = raw.get("data", raw)
    author = data.get("author", {})
    content = data.get("content", "")

    sender_id = author.get("user_openid", "")
    message_id = data.get("id", "")
    nickname = author.get("username", "")

    segments = _parse_message_content(content, data)
    raw_text = _extract_plain_text(segments).strip()

    return LoyanEvent(
        sender_id=sender_id,
        target_id=sender_id,
        chat_type="private",
        segments=segments,
        raw_text=raw_text,
        message_id=message_id,
        nickname=nickname,
        is_at_bot=False,
        raw_data=data,
        source=source,
    )


def _parse_message_content(content: str, data: dict) -> List[LoyanMsg]:
    """解析消息内容为 LoyanMsg 列表

    QQ 官方消息可能包含：
    - 纯文本
    - @提及（mentions 字段）
    - 图片（attachments 中）
    - 语音（attachments 中）
    - 文件（attachments 中）
    - 视频（attachments 中）
    - 回复引用（message_reference 字段）
    """
    segments: List[LoyanMsg] = []

    # 文本内容
    if content:
        segments.append(LoyanText(text=content))

    # 回复引用（message_reference 字段）
    message_reference = data.get("message_reference")
    if message_reference and isinstance(message_reference, dict):
        ref_message_id = message_reference.get("message_id", "")
        if ref_message_id:
            segments.append(LoyanReply(message_id=ref_message_id))

    # 附件（图片、语音、文件、视频等）
    attachments = data.get("attachments", [])
    for att in attachments:
        content_type = att.get("content_type", "")
        url = att.get("url", "")
        filename = att.get("filename", "")

        if content_type.startswith("image/"):
            segments.append(LoyanImage(url=url))
        elif content_type == "voice":
            # 语音消息：提取 asr 转文字 + 语音 URL
            asr_text = att.get("asr_refer_text", "")
            voice_url = att.get("url", "") or att.get("voice_wav_url", "")
            if asr_text:
                segments.append(LoyanText(text=f"[语音]{asr_text}"))
            if voice_url:
                segments.append(LoyanVoice(file_path=voice_url))
        elif content_type == "file":
            if url:
                segments.append(LoyanFile(url=url, file_path=filename))
        elif content_type.startswith("video/"):
            if url:
                segments.append(LoyanVideo(url=url, file_path=filename))

    # @提及解析（从 mentions 字段）
    mentions = data.get("mentions", [])
    for mention in mentions:
        target_id = mention.get("id", "")
        segments.append(LoyanAt(target_id=target_id))

    return segments


def _extract_plain_text(segments: List[LoyanMsg]) -> str:
    """从消息段中提取纯文本（包含标签）"""
    parts = []
    for seg in segments:
        if isinstance(seg, LoyanText):
            parts.append(seg.text)
        elif isinstance(seg, LoyanReply):
            parts.append(f"[回复:{seg.message_id}]")
        elif isinstance(seg, LoyanFile):
            if seg.file_path:
                parts.append(f"[文件:{seg.file_path}]")
            elif seg.url:
                parts.append(f"[文件:{seg.url}]")
    return "".join(parts)


# ============================================================
# 出站：LoyanMsg → QQ 官方消息格式
# ============================================================

def build_send_payload(
    target: str,
    segments: List[LoyanMsg],
    chat_type: str,
    msg_id: str = "",
) -> dict:
    """构建发送消息的 HTTP 请求体

    Args:
        target: 目标 ID（openid 或 group_openid）
        segments: LoyanMsg 消息段列表
        chat_type: "private" | "group"
        msg_id: 被动回复关联的消息 ID

    Returns:
        包含 msg_type, content, image_url, msg_id 的字典
    """
    content, msg_type, image_url, voice_url, reply_msg_id = _convert_segments(segments)

    # 优先使用 segments 中的 LoyanReply msg_id，其次使用传入的 msg_id
    final_msg_id = reply_msg_id or msg_id

    payload = {
        "msg_type": msg_type,
        "content": content,
    }

    # 被动回复需要带 msg_id
    if final_msg_id:
        payload["msg_id"] = final_msg_id

    # 图片 URL（需要后续上传获取 file_info）
    if image_url:
        payload["image_url"] = image_url

    # 语音 URL（需要后续上传获取 file_info）
    if voice_url:
        payload["voice_url"] = voice_url

    return payload


def _convert_segments(segments: List[LoyanMsg]) -> tuple:
    """将 LoyanMsg 列表转换为 QQ 官方消息格式

    Returns:
        (content, msg_type, image_url, voice_url, msg_id)
        - content: 文本内容
        - msg_type: 0=文本
        - image_url: 图片 URL（需要后续上传获取 file_info）
        - voice_url: 语音 URL（需要后续上传获取 file_info）
        - msg_id: 被动回复关联的消息 ID（从 LoyanReply 提取）
    """
    text_parts = []
    has_image = False
    image_url = ""
    voice_url = ""
    reply_msg_id = ""

    for seg in segments:
        if isinstance(seg, LoyanText):
            text_parts.append(seg.text)
        elif isinstance(seg, str):
            # 裸字符串（非 LoyanMsg 类型），也作为文本处理
            if seg.strip():
                text_parts.append(seg)
        elif isinstance(seg, LoyanAt):
            # QQ 官方群聊不需要显式 @，消息会自动 @ 触发者
            pass
        elif isinstance(seg, LoyanImage):
            has_image = True
            url = seg.url or seg.file_path
            if url:
                image_url = url
        elif isinstance(seg, LoyanVoice):
            voice_url = seg.file_path or seg.url
        elif isinstance(seg, LoyanReply):
            # 提取 msg_id 用于被动回复
            reply_msg_id = seg.message_id
        elif isinstance(seg, LoyanFile):
            _logger.warning(f"不支持的消息段类型: {type(seg).__name__}")
        elif isinstance(seg, LoyanVideo):
            _logger.warning(f"不支持的消息段类型: {type(seg).__name__}")
        elif isinstance(seg, LoyanForward):
            _logger.warning(f"不支持的消息段类型: {type(seg).__name__}")

    content = "".join(text_parts)

    # 语音优先（语音和文本不能同时发送）
    if voice_url:
        return "", 0, "", voice_url, reply_msg_id
    elif image_url:
        # 有图片，返回图片 URL，后续需要上传获取 file_info
        return content, 0, image_url, "", reply_msg_id
    elif content:
        # 纯文本
        return content, 0, "", "", reply_msg_id
    else:
        # 空消息 fallback
        return "", 0, "", "", reply_msg_id
