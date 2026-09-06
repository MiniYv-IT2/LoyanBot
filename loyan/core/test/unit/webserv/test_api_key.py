"""API Key 认证单元测试 — 验证 / 权限检查"""

from loyan.core.webserv.panel.auth import verify_api_key, check_permission


class TestVerifyApiKey:
    def test_invalid_key_format(self):
        assert verify_api_key("") is None
        assert verify_api_key("short") is None
        assert verify_api_key("x" * 63) is None
        assert verify_api_key("x" * 65) is None

    def test_unknown_key(self):
        assert verify_api_key("a" * 64) is None

    def test_none_key(self):
        assert verify_api_key(None) is None


class TestCheckPermission:
    def test_read_perm_always_allowed(self):
        assert check_permission(["read"], "read") is True
        assert check_permission(["read", "write"], "read") is True

    def test_write_perm_required(self):
        assert check_permission(["read"], "write") is False
        assert check_permission(["read", "write"], "write") is True
