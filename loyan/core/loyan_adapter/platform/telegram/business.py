"""Telegram 业务事件转换 — Update 中的进群/退群/禁言事件 → BusinessEvent

覆盖：
- service message 的 new_chat_members / left_chat_member
- chat_member 更新的进群/被踢/退群/禁言/解禁
"""

import time
from typing import Optional


def parse_telegram_business(update) -> Optional["BusinessEvent"]:
    """将 Telegram Update 转换为 BusinessEvent；不支持返回 None"""
    try:
        from loyan.core.event import EventType, BusinessEvent
    except ImportError:
        return None

    if update is None:
        return None
    for parse in (_parse_chat_member, _parse_service_message):
        biz = parse(update, EventType, BusinessEvent)
        if biz is not None:
            return biz
    return None


def _can_send_messages(member) -> bool:
    if member is None:
        return True
    status = getattr(member, "status", "")
    if status in ("creator", "administrator"):
        return True
    if status == "restricted":
        return bool(getattr(member, "can_send_messages", False))
    return status == "member"


def _restrict_duration(member) -> int:
    until = getattr(member, "until_date", None)
    if until is None:
        return 0
    return max(0, int(until - time.time()))


def _parse_chat_member(update, EventType, BusinessEvent):
    cm = getattr(update, "chat_member", None)
    if cm is None:
        return None
    chat = getattr(cm, "chat", None)
    if chat is None or getattr(chat, "type", "") == "private":
        return None
    group_id = str(chat.id)
    new_member = getattr(cm, "new_chat_member", None)
    old_member = getattr(cm, "old_chat_member", None)
    user = getattr(new_member, "user", None) if new_member else None
    if user is None:
        return None
    user_id = str(getattr(user, "id", ""))
    operator = getattr(cm, "from_user", None)
    operator_id = str(getattr(operator, "id", "")) if operator else ""
    old_status = getattr(old_member, "status", "") if old_member else ""
    new_status = getattr(new_member, "status", "")

    # 禁言/解禁：仅当新旧状态都在群内（member/admin/creator/restricted）时判断
    in_group = ("member", "administrator", "creator", "restricted")
    old_in = old_status in in_group
    new_in = new_status in in_group
    old_can = _can_send_messages(old_member)
    new_can = _can_send_messages(new_member)
    if old_in and new_in and old_can != new_can:
        if not new_can:
            return BusinessEvent(
                type=EventType.GROUP_MEMBER_MUTED,
                payload={
                    "group_id": group_id,
                    "user_id": user_id,
                    "operator_id": operator_id,
                    "duration": _restrict_duration(new_member),
                },
                source="telegram",
            )
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_UNMUTED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
            },
            source="telegram",
        )

    # 进群/被踢/退群
    if new_status in ("member", "administrator", "creator") and old_status in ("left", "kicked"):
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_JOINED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
                "at": 0,
            },
            source="telegram",
        )
    if new_status == "kicked" and old_status != "kicked":
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_KICKED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
            },
            source="telegram",
        )
    if new_status == "left" and old_status not in ("left", "kicked"):
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_LEFT,
            payload={"group_id": group_id, "user_id": user_id},
            source="telegram",
        )
    return None


def _parse_service_message(update, EventType, BusinessEvent):
    msg = getattr(update, "effective_message", None)
    if msg is None:
        return None
    chat = getattr(msg, "chat", None)
    if chat is None:
        return None
    group_id = str(chat.id)

    new_members = getattr(msg, "new_chat_members", None)
    if new_members:
        member = new_members[0]
        operator = getattr(msg, "from_user", None)
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_JOINED,
            payload={
                "group_id": group_id,
                "user_id": str(getattr(member, "id", "")),
                "operator_id": str(getattr(operator, "id", "")) if operator else "",
                "at": int(getattr(msg, "date", 0) or 0),
            },
            source="telegram",
        )

    left = getattr(msg, "left_chat_member", None)
    if left is not None:
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_LEFT,
            payload={"group_id": group_id, "user_id": str(getattr(left, "id", ""))},
            source="telegram",
        )
    return None
