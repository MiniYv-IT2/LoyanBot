"""认证中间件集成测试"""

import pytest

from loyan.core.webserv.panel import _is_public_path


class TestAuthMiddlewarePublicRoutes:
    """验证所有公开路由确实免认证"""

    def test_auth_routes(self):
        assert _is_public_path("/api/loyanui/auth/login") is True
        assert _is_public_path("/api/loyanui/auth/captcha") is True
        assert _is_public_path("/api/loyanui/auth/verify") is True

    def test_version_and_schemas(self):
        assert _is_public_path("/api/loyanui/version") is True
        assert _is_public_path("/api/loyanui/adapter/types") is True
        assert _is_public_path("/api/loyanui/adapter/schema/qqbot") is True
        assert _is_public_path("/api/loyanui/providers/types") is True
        assert _is_public_path("/api/loyanui/providers/vendors") is True
        assert _is_public_path("/api/loyanui/settings/schema") is True
        assert _is_public_path("/api/loyanui/user-config/schema") is True
        assert _is_public_path("/api/loyanui/panel/schema") is True

    def test_update_and_health(self):
        assert _is_public_path("/api/loyanui/update/check") is True
        assert _is_public_path("/api/loyanui/update/changelog") is True
        assert _is_public_path("/health") is True
        assert _is_public_path("/metrics") is True

    def test_qqbot(self):
        assert _is_public_path("/api/loyanui/qqbot/qr-login/create") is True
        assert _is_public_path("/api/loyanui/qqbot/qr-login/poll") is True


class TestAuthMiddlewareProtectedRoutes:
    """验证所有需要认证的路由确实被保护"""

    def test_panel_routes_restricted(self):
        assert _is_public_path("/api/loyanui/plugins") is False
        assert _is_public_path("/api/loyanui/providers") is False
        assert _is_public_path("/api/loyanui/settings") is False
        assert _is_public_path("/api/loyanui/user-config") is False
        assert _is_public_path("/api/loyanui/panel") is False
        assert _is_public_path("/api/loyanui/instances") is False
        assert _is_public_path("/api/loyanui/chat/sessions") is False
        assert _is_public_path("/api/loyanui/chat/stream") is False
        assert _is_public_path("/api/loyanui/chat/tasks") is False
        assert _is_public_path("/api/loyanui/chat/personas") is False
        assert _is_public_path("/api/loyanui/store/plugins") is False
        assert _is_public_path("/api/loyanui/test/send") is False
        assert _is_public_path("/api/loyanui/update/apply") is False

    def test_apikeys_admin_only(self):
        assert _is_public_path("/api/loyanui/apikeys") is False
        assert _is_public_path("/api/loyanui/apikeys/some-id") is False

    def test_read_only_routes(self):
        # send, plugins, providers 是只读，需要认证
        assert _is_public_path("/api/loyanui/send") is False
        assert _is_public_path("/api/loyanui/plugins") is False
        assert _is_public_path("/api/loyanui/providers") is False
        assert _is_public_path("/api/loyanui/providers/some-id/models") is False
