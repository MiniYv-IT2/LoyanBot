"""EventType / Payload / validate_payload / BusinessEvent 单元测试

- 71 个事件类型存在且值唯一
- validate_payload：每个类型合法 payload 通过；缺必填/类型错误抛 ValueError
- BusinessEvent cancel 语义
"""

import dataclasses

import pytest

from loyan.core.event import BusinessEvent, EventType
from loyan.core.event.types import _PAYLOAD_MAP, validate_payload

# 期望的事件域数量（10 域）
_DOMAIN_EXPECTED = {
    "message": 2,
    "group": 12,
    "friend": 4,
    "platform": 5,
    "instance": 5,
    "plugin": 10,
    "notification": 4,
    "system": 5,
    "user": 3,
    "ai": 21,
}

EXPECTED_TOTAL = sum(_DOMAIN_EXPECTED.values())


def _required_fields(cls) -> list:
    """无默认值字段（必填）"""
    return [
        f
        for f in dataclasses.fields(cls)
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
    ]


def _sample_value(field) -> object:
    """按字段类型构造合法样本值"""
    if field.type == "str":
        return "sample"
    if field.type == "int":
        return 1
    if field.type == "bool":
        return True
    if field.type == "float":
        return 0.5
    if field.type == "list":
        return []
    return None


def _valid_data(event_type: EventType) -> dict:
    """为某事件类型构造满足必填字段的合法 data dict"""
    cls = _PAYLOAD_MAP[event_type]
    return {f.name: _sample_value(f) for f in _required_fields(cls)}


class TestEventType:
    def test_count_71(self):
        assert len(EventType) == EXPECTED_TOTAL == 71

    def test_values_unique(self):
        values = [e.value for e in EventType]
        assert len(set(values)) == len(values)

    def test_domains(self):
        domains = {
            "message": sum(1 for e in EventType if e.value.startswith("message")),
            "group": sum(1 for e in EventType if e.value.startswith("group_")),
            "friend": sum(1 for e in EventType if e.value.startswith("friend_")),
            "platform": sum(1 for e in EventType if e.value.startswith("platform_")),
            "instance": sum(1 for e in EventType if e.value.startswith("instance_")),
            "plugin": sum(1 for e in EventType if e.value.startswith("plugin_")),
            "notification": sum(1 for e in EventType if e.value.startswith("system_announcement")
                                or e.value.startswith("system_maintenance")
                                or e.value.startswith("system_update")
                                or e.value.startswith("system_alert")),
            "system": sum(1 for e in EventType if e.value.startswith("system_")
                          and not (e.value.startswith("system_announcement")
                                   or e.value.startswith("system_maintenance")
                                   or e.value.startswith("system_update")
                                   or e.value.startswith("system_alert"))),
            "user": sum(1 for e in EventType if e.value.startswith("user_")),
            "ai": sum(1 for e in EventType if e.value.startswith("ai_")),
        }
        assert domains == _DOMAIN_EXPECTED

    def test_roundtrip_by_value(self):
        # 值可逆：str 值可还原回枚举（订阅 key biz:{type.value} 依赖此）
        for e in EventType:
            assert EventType(e.value) is e


class TestValidatePayload:
    def test_every_type_valid_payload_passes(self):
        # 每个事件类型构造合法 payload 均通过校验且类型正确
        for event_type in EventType:
            data = _valid_data(event_type)
            payload = validate_payload(event_type, data)
            assert payload.__class__ is _PAYLOAD_MAP[event_type]

    def test_defaults_applied(self):
        # 未提供的可选字段使用默认值
        payload = validate_payload(
            EventType.GROUP_MEMBER_JOINED, {"group_id": "1", "user_id": "2"}
        )
        assert payload.operator_id == ""
        assert payload.at == 0

    def test_missing_required_raises(self):
        # 缺必填字段 → ValueError（仅对存在必填字段的类型）
        checked = 0
        for event_type, cls in _PAYLOAD_MAP.items():
            required = _required_fields(cls)
            if not required:
                continue
            data = _valid_data(event_type)
            del data[required[0].name]
            with pytest.raises(ValueError, match="missing required field"):
                validate_payload(event_type, data)
            checked += 1
        # 至少覆盖了带必填字段的类型（其余类型字段全部可选）
        assert checked >= 40

    def test_wrong_type_raises(self):
        # 字段类型错误 → ValueError（跳过 Any 类型字段）
        checked = 0
        for event_type, cls in _PAYLOAD_MAP.items():
            target = None
            for f in dataclasses.fields(cls):
                if f.type == "Any":
                    continue
                target = f
                break
            if target is None:
                continue
            data = _valid_data(event_type)
            data[target.name] = _wrong_value(target.type)
            with pytest.raises(ValueError, match="expects"):
                validate_payload(event_type, data)
            checked += 1
        assert checked >= 60

    def test_unknown_event_type_rejected(self):
        with pytest.raises(ValueError, match="unknown event type"):
            validate_payload("not_an_event", {})


def _wrong_value(annotation: str) -> object:
    """构造与注解类型不符的值"""
    if annotation == "str":
        return 123
    if annotation == "int":
        return "not-int"
    if annotation == "bool":
        return "not-bool"
    if annotation == "float":
        return "not-float"
    if annotation == "list":
        return "not-list"
    return None


class TestBusinessEvent:
    def test_defaults(self):
        ev = BusinessEvent(EventType.SYSTEM_STARTUP, object())
        assert ev.source == ""
        assert ev.adapter_tag == ""
        assert ev.timestamp == 0.0
        assert ev.cancelled is False

    def test_cancel_semantics(self):
        ev = BusinessEvent(EventType.FRIEND_REQUEST, object())
        assert not ev.cancelled
        ev.cancel()
        assert ev.cancelled is True
