"""Satori 事件转换 — Satori Event → LoyanEvent

职责：
- satori_event_to_loyan: 将 Satori 事件转换为 LoyanEvent
"""

import logging
from typing import Optional

from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.platform.satori.message import satori_to_loyan, extract_plain_text
from loyan.core.loyan_adapter.message import LoyanText, LoyanAt

_logger = logging.getLogger("Adapter.Satori.event")


def _get(obj, key, default=None):
    """兼容 dict 与 satori 模型对象的字段提取"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    if obj is None:
        return default
    return getattr(obj, key, default)


def satori_event_to_business(raw) -> Optional["BusinessEvent"]:
    """Satori 事件 → BusinessEvent；不支持返回 None

    支持 member_added/member_removed/friend_request（兼容连字符风格类型名）。
    raw 可为 dict 或 satori 模型对象。
    """
    try:
        from loyan.core.event import EventType, BusinessEvent
    except ImportError:
        return None

    event_type = str(_get(raw, "type", "")).replace("-", "_")
    guild = _get(raw, "guild") or {}
    channel = _get(raw, "channel") or {}
    user = _get(raw, "user") or {}
    operator = _get(raw, "operator") or {}
    group_id = str(_get(guild, "id") or _get(channel, "parent_id") or "")
    user_id = str(_get(user, "id") or "")
    operator_id = str(_get(operator, "id") or "")

    if event_type == "member_added":
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_JOINED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
                "at": int(_get(raw, "timestamp", 0) or 0),
            },
            source="satori",
        )

    if event_type == "member_removed":
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_LEFT,
            payload={"group_id": group_id, "user_id": user_id},
            source="satori",
        )

    if event_type == "friend_request":
        # Satori 好友申请：请求者通常在 operator，fallback 到 user
        uid = operator_id or user_id
        nickname = str(_get(operator, "name") or _get(user, "name") or "")
        message = str(_get(operator, "message") or _get(raw, "message") or "")
        return BusinessEvent(
            type=EventType.FRIEND_REQUEST,
            payload={"user_id": uid, "nickname": nickname, "message": message},
            source="satori",
        )

    return None


def satori_event_to_loyan(
    satori_event: dict,
    tag: IdentityTag,
) -> Optional[LoyanEvent]:
    """将 Satori 事件转换为 LoyanEvent

    Args:
        satori_event: Satori 事件数据
        tag: 来源适配器标签

    Returns:
        转换成功返回 LoyanEvent，不关心的事件返回 None
    """
    event_type = satori_event.get("type", "")

    if event_type == "message_created":
        return _handle_message_created(satori_event, tag)
    elif event_type in ("member_added", "member_removed"):
        _logger.debug(f"Satori 群组成员变动事件: {event_type}")
        return None
    elif event_type == "friend_request":
        _logger.debug("Satori 好友请求事件")
        return None
    elif event_type == "message_updated":
        _logger.debug("Satori 消息更新事件")
        return None
    elif event_type == "message_deleted":
        _logger.debug("Satori 消息删除事件")
        return None
    else:
        _logger.debug(f"忽略 Satori 事件类型: {event_type}")
        return None

def _handle_message_created(satori_event: dict, tag: IdentityTag) -> Optional[LoyanEvent]:
    """处理消息创建事件"""
    # 提取消息数据
    message = satori_event.get("message", {})
    if not message:
        _logger.debug("Satori 事件无消息数据")
        return None

    # 提取发送者
    user = satori_event.get("user", {})
    sender_id = user.get("id", "")
    nickname = user.get("name", "")

    if not sender_id:
        _logger.debug("Satori 事件无发送者 ID")
        return None

    # 提取目标
    channel = satori_event.get("channel", {})
    target_id = channel.get("id", "")
    channel_type = channel.get("type", "")

    # 判断私聊/群聊
    chat_type = "private" if channel_type == "private" else "group"

    # 转换消息内容
    content = message.get("content", "")
    segments = satori_to_loyan(content)

    # 提取纯文本
    raw_text = extract_plain_text(segments).strip()

    # 提取消息 ID
    message_id = message.get("id", "")

    # 检测 @机器人
    self_id = satori_event.get("self", {}).get("id", "")
    is_at_bot = any(
        seg.target_id == self_id
        for seg in segments
        if isinstance(seg, LoyanAt)
    )

    return LoyanEvent(
        sender_id=sender_id,
        target_id=target_id or sender_id,
        chat_type=chat_type,
        segments=segments,
        raw_text=raw_text,
        message_id=message_id,
        nickname=nickname,
        is_at_bot=is_at_bot,
        raw_data=satori_event,
        source=tag,
    )
