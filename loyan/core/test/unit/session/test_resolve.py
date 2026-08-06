"""resolve 单元测试 — IM 会话 ID 解析规则

覆盖 resolve_im_session_id 格式与 resolve_from_context 提取逻辑。
"""

from types import SimpleNamespace

from loyan.core.loyan_session.resolve import (
    resolve_from_context,
    resolve_im_session_id,
)


def test_resolve_im_session_id_format():
    sid = resolve_im_session_id("onebot", "inst_a", "private", "10001")
    assert sid == "chat_onebot_inst_a_private_10001"


def test_resolve_im_session_id_group_public_default():
    sid = resolve_im_session_id("telegram", "inst_b", "group", "777")
    assert sid == "chat_telegram_inst_b_group_777"


def test_resolve_im_session_id_group_sub_id():
    sid = resolve_im_session_id("telegram", "inst_b", "group", "777", sub_id="u1")
    assert sid == "chat_telegram_inst_b_group_777_u1"


def test_resolve_im_session_id_empty_peer():
    assert resolve_im_session_id("onebot", "inst_a", "private", "") == ""
    assert resolve_im_session_id("onebot", "inst_a", "group", None) == ""


def _ctx(chat_type, sender_id, target_id, platform="onebot", instance_id="inst_x"):
    tag = SimpleNamespace(platform=platform, instance_id=instance_id)
    return SimpleNamespace(adapter_tag=tag, chat_type=chat_type,
                           sender_id=sender_id, target_id=target_id)


def test_resolve_from_context_private_uses_sender():
    ctx = _ctx("private", "10001", "10001")
    assert resolve_from_context(ctx) == "chat_onebot_inst_x_private_10001"


def test_resolve_from_context_group_uses_target():
    ctx = _ctx("group", "10001", "888")
    assert resolve_from_context(ctx) == "chat_onebot_inst_x_group_888"


def test_resolve_from_context_no_tag():
    ctx = SimpleNamespace(adapter_tag=None, chat_type="private",
                          sender_id="1", target_id="1")
    assert resolve_from_context(ctx) == "chat___private_1"
