"""面板中间件认证单元测试 — JWT / API Key / 公开路径"""

import pytest
from unittest.mock import MagicMock, patch

from loyan.core.webserv.panel import (
    _is_public_path, _get_jwt_token, _get_api_key,
)


class TestPublicPath:
    def test_auth_routes_public(self):
        assert _is_public_path("/api/loyanui/auth/login") is True
        assert _is_public_path("/api/loyanui/auth/captcha") is True
        assert _is_public_path("/api/loyanui/auth/verify") is True

    def test_version_public(self):
        assert _is_public_path("/api/loyanui/version") is True

    def test_adapter_schema_public(self):
        assert _is_public_path("/api/loyanui/adapter/types") is True
        assert _is_public_path("/api/loyanui/adapter/schema/qqbot") is True

    def test_provider_types_public(self):
        assert _is_public_path("/api/loyanui/providers/types") is True
        assert _is_public_path("/api/loyanui/providers/vendors") is True

    def test_schema_routes_public(self):
        assert _is_public_path("/api/loyanui/user-config/schema") is True
        assert _is_public_path("/api/loyanui/settings/schema") is True
        assert _is_public_path("/api/loyanui/panel/schema") is True

    def test_update_public(self):
        assert _is_public_path("/api/loyanui/update/check") is True
        assert _is_public_path("/api/loyanui/update/changelog") is True

    def test_health_metrics_public(self):
        assert _is_public_path("/health") is True
        assert _is_public_path("/metrics") is True

    def test_qqbot_public(self):
        assert _is_public_path("/api/loyanui/qqbot/qr-login/create") is True
        assert _is_public_path("/api/loyanui/qqbot/qr-login/poll") is True

    def test_jwt_protected_routes(self):
        assert _is_public_path("/api/loyanui/plugins") is False
        assert _is_public_path("/api/loyanui/providers") is False
        assert _is_public_path("/api/loyanui/chat/sessions") is False
        assert _is_public_path("/api/loyanui/settings") is False
        assert _is_public_path("/api/loyanui/instances") is False

    def test_read_only_routes(self):
        # send 和 plugins/providers 是只读，需要认证但不是公开
        assert _is_public_path("/api/loyanui/send") is False
        assert _is_public_path("/api/loyanui/plugins") is False
        assert _is_public_path("/api/loyanui/providers") is False

    def test_apikeys_admin_only(self):
        assert _is_public_path("/api/loyanui/apikeys") is False
        assert _is_public_path("/api/loyanui/apikeys/some-id") is False

    def test_root_not_public(self):
        assert _is_public_path("/") is False
        assert _is_public_path("/assets/index.js") is False


class TestGetJwtToken:
    def test_bearer_header(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = "Bearer mytoken123"
        mock_req.args.get.return_value = ""
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_jwt_token() == "mytoken123"

    def test_query_param_fallback(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = ""
        mock_req.args.get.return_value = "querytoken"
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_jwt_token() == "querytoken"

    def test_no_token(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = ""
        mock_req.args.get.return_value = ""
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_jwt_token() == ""


class TestGetApiKey:
    def test_header_present(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = "abc123hex"
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_api_key() == "abc123hex"

    def test_header_missing(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = ""
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_api_key() == ""

    def test_whitespace_stripped(self):
        mock_req = MagicMock()
        mock_req.headers.get.return_value = "  abc123  "
        with patch("loyan.core.webserv.panel._quart_request", mock_req):
            assert _get_api_key() == "abc123"
