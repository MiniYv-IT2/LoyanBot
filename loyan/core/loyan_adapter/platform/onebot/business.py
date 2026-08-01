"""OneBot 业务事件转换 — OneBot notice 事件 → BusinessEvent

仅处理 post_type="notice" 的群组/好友通知事件；
消息事件、元事件、未知通知类型返回 None。
"""

from typing import Optional


def parse_onebot_business(raw: dict) -> Optional["BusinessEvent"]:
    """将 OneBot 原始事件转换为 BusinessEvent

    Args:
        raw: OneBot 事件 JSON（dict）

    Returns:
        识别为业务事件返回 BusinessEvent，否则返回 None
    """
    try:
        from loyan.core.event import EventType, BusinessEvent
    except ImportError:
        return None

    if not isinstance(raw, dict) or raw.get("post_type") != "notice":
        return None

    notice_type = raw.get("notice_type", "")
    group_id = str(raw.get("group_id", ""))
    user_id = str(raw.get("user_id", ""))
    operator_id = str(raw.get("operator_id", ""))

    if notice_type == "group_increase":
        # 成员入群（sub_type: approve/invite/self）
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_JOINED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
                "at": int(raw.get("time", 0) or 0),
            },
            source="onebot",
        )

    if notice_type == "group_decrease":
        # 成员退群（sub_type: leave）或被踢（sub_type: kick/kick_me）
        if raw.get("sub_type") == "leave":
            return BusinessEvent(
                type=EventType.GROUP_MEMBER_LEFT,
                payload={"group_id": group_id, "user_id": user_id},
                source="onebot",
            )
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_KICKED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
            },
            source="onebot",
        )

    if notice_type == "group_admin":
        # 群管变更（sub_type: set/unset）
        return BusinessEvent(
            type=EventType.GROUP_ADMIN_CHANGED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "is_admin": raw.get("sub_type") == "set",
                "operator_id": operator_id,
            },
            source="onebot",
        )

    if notice_type == "group_ban":
        # 禁言：user_id=0 为全体禁言，否则单人禁言；duration=0 为解除
        duration = int(raw.get("duration", 0) or 0)
        if not user_id or user_id == "0":
            if duration <= 0:
                return BusinessEvent(
                    type=EventType.GROUP_UNMUTED,
                    payload={"group_id": group_id, "operator_id": operator_id},
                    source="onebot",
                )
            return BusinessEvent(
                type=EventType.GROUP_MUTED,
                payload={
                    "group_id": group_id,
                    "operator_id": operator_id,
                    "duration": duration,
                },
                source="onebot",
            )
        if duration <= 0:
            return BusinessEvent(
                type=EventType.GROUP_MEMBER_UNMUTED,
                payload={
                    "group_id": group_id,
                    "user_id": user_id,
                    "operator_id": operator_id,
                },
                source="onebot",
            )
        return BusinessEvent(
            type=EventType.GROUP_MEMBER_MUTED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "operator_id": operator_id,
                "duration": duration,
            },
            source="onebot",
        )

    if notice_type == "group_recall":
        # 群消息撤回（OneBot 不提供消息内容）
        return BusinessEvent(
            type=EventType.GROUP_RECALLED,
            payload={
                "group_id": group_id,
                "operator_id": operator_id,
                "message_id": str(raw.get("message_id", "")),
                "message": "",
            },
            source="onebot",
        )

    if notice_type == "friend_add":
        return BusinessEvent(
            type=EventType.FRIEND_ADDED,
            payload={"user_id": user_id},
            source="onebot",
        )

    if notice_type == "friend_recall":
        return BusinessEvent(
            type=EventType.FRIEND_RECALLED,
            payload={
                "user_id": user_id,
                "message_id": str(raw.get("message_id", "")),
            },
            source="onebot",
        )

    if notice_type == "group_upload":
        file_info = raw.get("file", {})
        if not isinstance(file_info, dict):
            file_info = {}
        return BusinessEvent(
            type=EventType.GROUP_FILE_UPLOADED,
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "file_name": str(file_info.get("name", "")),
                "file_size": int(file_info.get("size", 0) or 0),
            },
            source="onebot",
        )

    # 未知通知类型
    return None
