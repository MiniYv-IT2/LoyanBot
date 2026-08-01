"""平台适配器 parse_business_event 单元测试

直接调用各平台 parse_business_event，无需真实连接平台。
types.py 未就绪时用最小桩（sys.modules 注入）兜底，保证测试可运行。
"""

import dataclasses
import sys
import time
import types as _pymod
from types import SimpleNamespace

import pytest

from loyan.core.loyan_adapter.platform.onebot.http import LoyanOneBot
from loyan.core.loyan_adapter.platform.onebot.ws import LoyanOneBotWS
from loyan.core.loyan_adapter.platform.satori.adapter import SatoriAdapter
from loyan.core.loyan_adapter.platform.qq_official.adapter import QQOfficialAdapter
from loyan.core.loyan_adapter.platform.telegram.adapter import TelegramAdapter

_EVENT_NAMES = [
    "GROUP_MEMBER_JOINED", "GROUP_MEMBER_LEFT", "GROUP_MEMBER_KICKED",
    "GROUP_ADMIN_CHANGED", "GROUP_MUTED", "GROUP_UNMUTED",
    "GROUP_MEMBER_MUTED", "GROUP_MEMBER_UNMUTED", "GROUP_RECALLED",
    "GROUP_FILE_UPLOADED", "FRIEND_REQUEST", "FRIEND_ADDED",
    "FRIEND_DELETED", "FRIEND_RECALLED",
]


@pytest.fixture()
def biz_types(monkeypatch):
    """返回 (EventType, BusinessEvent)；types.py 未就绪时注入最小桩"""
    try:
        from loyan.core.event import EventType, BusinessEvent
        return EventType, BusinessEvent
    except ImportError:
        pass
    mod = _pymod.ModuleType("loyan.core.event")
    mod.EventType = type("EventType", (), {name: name for name in _EVENT_NAMES})

    @dataclasses.dataclass
    class BusinessEventStub:
        type: object
        payload: dict
        source: str = ""

    mod.BusinessEvent = BusinessEventStub
    monkeypatch.setitem(sys.modules, "loyan.core.event", mod)
    return mod.EventType, BusinessEventStub


class TestOneBotBusiness:
    def setup_method(self):
        self.adapter = LoyanOneBot()

    def test_group_increase(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_increase",
            "group_id": 10001, "user_id": 20001, "operator_id": 30001,
            "sub_type": "approve", "time": 1700000000, "extra": "x",
        })
        assert biz is not None
        assert biz.type == EventType.GROUP_MEMBER_JOINED
        assert biz.source == "onebot"
        assert biz.payload["group_id"] == "10001"
        assert biz.payload["user_id"] == "20001"
        assert biz.payload["operator_id"] == "30001"
        assert biz.payload["at"] == 1700000000

    def test_group_decrease_leave(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_decrease",
            "group_id": 1, "user_id": 2, "sub_type": "leave",
        })
        assert biz.type == EventType.GROUP_MEMBER_LEFT
        assert biz.payload == {"group_id": "1", "user_id": "2"}

    def test_group_decrease_kick(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_decrease",
            "group_id": 1, "user_id": 2, "operator_id": 3, "sub_type": "kick",
        })
        assert biz.type == EventType.GROUP_MEMBER_KICKED
        assert biz.payload["operator_id"] == "3"

    def test_group_admin_set_unset(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_admin",
            "group_id": 1, "user_id": 2, "sub_type": "set",
        })
        assert biz.type == EventType.GROUP_ADMIN_CHANGED
        assert biz.payload["is_admin"] is True
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_admin",
            "group_id": 1, "user_id": 2, "sub_type": "unset",
        })
        assert biz.payload["is_admin"] is False

    def test_group_ban_all_and_lift(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_ban",
            "group_id": 1, "user_id": 0, "operator_id": 3, "duration": 600,
        })
        assert biz.type == EventType.GROUP_MUTED
        assert biz.payload["duration"] == 600
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_ban",
            "group_id": 1, "user_id": 0, "operator_id": 3, "duration": 0,
        })
        assert biz.type == EventType.GROUP_UNMUTED

    def test_group_ban_member_and_lift(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_ban",
            "group_id": 1, "user_id": 2, "operator_id": 3, "duration": 60,
        })
        assert biz.type == EventType.GROUP_MEMBER_MUTED
        assert biz.payload["user_id"] == "2"
        assert biz.payload["duration"] == 60
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_ban",
            "group_id": 1, "user_id": 2, "operator_id": 3, "duration": 0,
        })
        assert biz.type == EventType.GROUP_MEMBER_UNMUTED

    def test_group_recall(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_recall",
            "group_id": 1, "user_id": 2, "operator_id": 3, "message_id": 888,
        })
        assert biz.type == EventType.GROUP_RECALLED
        assert biz.payload["message_id"] == "888"
        assert biz.payload["message"] == ""

    def test_friend_add_and_recall(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "friend_add", "user_id": 2,
        })
        assert biz.type == EventType.FRIEND_ADDED
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "friend_recall",
            "user_id": 2, "message_id": 9,
        })
        assert biz.type == EventType.FRIEND_RECALLED

    def test_group_upload(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "group_upload",
            "group_id": 1, "user_id": 2,
            "file": {"name": "a.png", "size": 123},
        })
        assert biz.type == EventType.GROUP_FILE_UPLOADED
        assert biz.payload["file_name"] == "a.png"
        assert biz.payload["file_size"] == 123

    def test_unknown_and_non_notice(self):
        assert self.adapter.parse_business_event({
            "post_type": "notice", "notice_type": "some_unknown", "group_id": 1,
        }) is None
        assert self.adapter.parse_business_event({
            "post_type": "message", "message_type": "group", "raw_message": "hi",
        }) is None
        assert self.adapter.parse_business_event({"post_type": "meta_event"}) is None
        assert self.adapter.parse_business_event(None) is None

    def test_ws_adapter_delegates(self, biz_types):
        EventType, _ = biz_types
        ws = LoyanOneBotWS()
        biz = ws.parse_business_event({
            "post_type": "notice", "notice_type": "friend_add", "user_id": 5,
        })
        assert biz.type == EventType.FRIEND_ADDED


class TestSatoriBusiness:
    def setup_method(self):
        self.adapter = SatoriAdapter()

    def test_member_added(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "type": "member_added",
            "guild": {"id": "g1"},
            "channel": {"id": "c1", "parent_id": "g1", "type": "text"},
            "user": {"id": "u1", "name": "alice"},
            "operator": {"id": "o1"},
            "timestamp": 1700000000,
        })
        assert biz.type == EventType.GROUP_MEMBER_JOINED
        assert biz.source == "satori"
        assert biz.payload["group_id"] == "g1"
        assert biz.payload["user_id"] == "u1"
        assert biz.payload["operator_id"] == "o1"
        assert biz.payload["at"] == 1700000000

    def test_member_added_hyphen_type(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "type": "member-added", "guild": {"id": "g1"}, "user": {"id": "u1"},
        })
        assert biz.type == EventType.GROUP_MEMBER_JOINED

    def test_member_removed(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "type": "member_removed", "guild": {"id": "g1"}, "user": {"id": "u1"},
        })
        assert biz.type == EventType.GROUP_MEMBER_LEFT
        assert biz.payload == {"group_id": "g1", "user_id": "u1"}

    def test_friend_request(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event({
            "type": "friend_request",
            "operator": {"id": "u9", "name": "bob", "message": "hi"},
        })
        assert biz.type == EventType.FRIEND_REQUEST
        assert biz.payload["user_id"] == "u9"
        assert biz.payload["nickname"] == "bob"
        assert biz.payload["message"] == "hi"

    def test_unknown(self):
        assert self.adapter.parse_business_event({"type": "message_deleted"}) is None
        assert self.adapter.parse_business_event({"type": "member_updated"}) is None


class TestQQOfficialBusiness:
    def setup_method(self):
        self.adapter = QQOfficialAdapter("appid", "secret")

    def test_always_none(self):
        assert self.adapter.parse_business_event({"type": "C2C_MESSAGE_CREATE"}) is None
        assert self.adapter.parse_business_event({"type": "GROUP_AT_MESSAGE_CREATE"}) is None
        assert self.adapter.parse_business_event({"type": "FRIEND_ADD"}) is None
        assert self.adapter.parse_business_event({}) is None


def _cm(group_id, user_id, old_status, new_status, old_can=True, new_can=True,
        operator="300", until=None):
    def member(status, can, until_):
        return SimpleNamespace(
            user=SimpleNamespace(id=user_id), status=status,
            can_send_messages=can, until_date=until_,
        )
    return SimpleNamespace(
        chat=SimpleNamespace(id=group_id, type="supergroup"),
        from_user=SimpleNamespace(id=operator),
        old_chat_member=member(old_status, old_can, None),
        new_chat_member=member(new_status, new_can, until),
    )


def _svc_msg(group_id, new_ids=(), left_id=None):
    attrs = {
        "chat": SimpleNamespace(id=group_id),
        "from_user": SimpleNamespace(id="100"),
        "date": 1700000000,
        "new_chat_members": [SimpleNamespace(id=i) for i in new_ids] if new_ids else None,
        "left_chat_member": SimpleNamespace(id=left_id) if left_id else None,
    }
    return SimpleNamespace(chat_member=None, effective_message=SimpleNamespace(**attrs))


class TestTelegramBusiness:
    def setup_method(self):
        self.adapter = TelegramAdapter()

    def test_service_join(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event(_svc_msg("g1", new_ids=("u1",)))
        assert biz.type == EventType.GROUP_MEMBER_JOINED
        assert biz.source == "telegram"
        assert biz.payload["group_id"] == "g1"
        assert biz.payload["user_id"] == "u1"
        assert biz.payload["operator_id"] == "100"
        assert biz.payload["at"] == 1700000000

    def test_service_left(self, biz_types):
        EventType, _ = biz_types
        biz = self.adapter.parse_business_event(_svc_msg("g1", left_id="u2"))
        assert biz.type == EventType.GROUP_MEMBER_LEFT
        assert biz.payload["user_id"] == "u2"

    def test_chat_member_join(self, biz_types):
        EventType, _ = biz_types
        update = SimpleNamespace(chat_member=_cm("g1", "u1", "left", "member"),
                                 effective_message=None)
        biz = self.adapter.parse_business_event(update)
        assert biz.type == EventType.GROUP_MEMBER_JOINED
        assert biz.payload["operator_id"] == "300"

    def test_chat_member_kicked(self, biz_types):
        EventType, _ = biz_types
        update = SimpleNamespace(chat_member=_cm("g1", "u1", "member", "kicked"),
                                 effective_message=None)
        biz = self.adapter.parse_business_event(update)
        assert biz.type == EventType.GROUP_MEMBER_KICKED

    def test_chat_member_left(self, biz_types):
        EventType, _ = biz_types
        update = SimpleNamespace(chat_member=_cm("g1", "u1", "member", "left"),
                                 effective_message=None)
        biz = self.adapter.parse_business_event(update)
        assert biz.type == EventType.GROUP_MEMBER_LEFT

    def test_chat_member_muted(self, biz_types):
        EventType, _ = biz_types
        until = time.time() + 3600
        update = SimpleNamespace(
            chat_member=_cm("g1", "u1", "member", "restricted", True, False, until=until),
            effective_message=None,
        )
        biz = self.adapter.parse_business_event(update)
        assert biz.type == EventType.GROUP_MEMBER_MUTED
        assert biz.payload["user_id"] == "u1"
        assert 0 < biz.payload["duration"] <= 3600

    def test_chat_member_unmuted(self, biz_types):
        EventType, _ = biz_types
        update = SimpleNamespace(
            chat_member=_cm("g1", "u1", "restricted", "member", False, True),
            effective_message=None,
        )
        biz = self.adapter.parse_business_event(update)
        assert biz.type == EventType.GROUP_MEMBER_UNMUTED

    def test_private_chat_and_unknown(self):
        cm = SimpleNamespace(
            chat=SimpleNamespace(id="p1", type="private"),
            from_user=SimpleNamespace(id="300"),
            old_chat_member=SimpleNamespace(status="member"),
            new_chat_member=SimpleNamespace(status="left", user=SimpleNamespace(id="u1")),
        )
        update = SimpleNamespace(chat_member=cm, effective_message=None)
        assert self.adapter.parse_business_event(update) is None
        assert self.adapter.parse_business_event(
            SimpleNamespace(chat_member=None, effective_message=None)) is None
        assert self.adapter.parse_business_event(None) is None
