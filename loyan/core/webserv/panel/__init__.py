"""Panel domain — Web visualization robot management.

Structure:
  server.py    Core service: start/port/retry
  static.py    Core service: static files
  commands.py  Core service: /panel chat command
  auth/        Authentication (token/password/captcha)
  api/         Route layer (receive/validate/return)
  service/     Business layer (logic/orchestration/decrypt)
"""

from loyan.core.webserv.quart import Quart, request as _quart_request

from loyan.core.webserv.panel.api import register_routes as _api_register
from loyan.core.webserv.panel.static import register_routes as _static_register

# 公开路由 - 无需认证（API内部有自己的鉴权逻辑）
_PUBLIC_PREFIXES = (
    "/api/loyanui/auth/",
    "/api/loyanui/version",
    "/api/loyanui/adapter/",
    "/api/loyanui/providers/types",
    "/api/loyanui/providers/vendors",
    "/api/loyanui/user-config/schema",
    "/api/loyanui/settings/schema",
    "/api/loyanui/panel/schema",
    "/api/loyanui/update/check",
    "/api/loyanui/update/changelog",
    "/health",
    "/metrics",
    "/api/loyanui/qqbot/",
    "/",
    "/api/loyanui/test/",
)

# 只读查询 - 支持 JWT 或 API Key
_READ_ONLY_PREFIXES = (
    "/api/loyanui/plugins",
    "/api/loyanui/providers",
    "/api/loyanui/providers/",
    "/api/loyanui/send",
    "/api/loyanui/account/",
)

# Admin操作 - 只支持 JWT
_ADMIN_PREFIXES = (
    "/api/loyanui/apikeys",
    "/api/loyanui/plugins/",
    "/api/loyanui/providers/",
    "/api/loyanui/instances",
    "/api/loyanui/chat/",
    "/api/loyanui/settings",
    "/api/loyanui/user-config",
    "/api/loyanui/panel",
    "/api/loyanui/store/",
    "/api/loyanui/update/",
    "/api/loyanui/test/",
)


def _get_jwt_token():
    auth = _quart_request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return _quart_request.args.get("token", "")


def _get_api_key():
    return _quart_request.headers.get("X-API-Key", "").strip()


def _is_public_path(path: str) -> bool:
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _is_read_only_path(path: str) -> bool:
    for prefix in _READ_ONLY_PREFIXES:
        if path == prefix or path.startswith(prefix):
            return True
    return False


def _is_admin_path(path: str) -> bool:
    for prefix in _ADMIN_PREFIXES:
        if path == prefix or path.startswith(prefix):
            return True
    return False


def create_panel_app() -> Quart:
    app = Quart("LoyanUI")
    _api_register(app)
    _static_register(app)

    @app.before_request
    async def auth_middleware():
        path = _quart_request.path
        
        # 公开路由
        if _is_public_path(path):
            return None
        
        # Admin路由 - 只支持JWT
        if _is_admin_path(path):
            token = _get_jwt_token()
            from loyan.core.webserv.panel.auth import verify_token
            if not token or not verify_token(token):
                from loyan.core.webserv.quart import jsonify
                return jsonify({"message": "unauthorized"}), 401
            return None
        
        # 只读路由 - 支持JWT或API Key
        if _is_read_only_path(path):
            # 先试API Key
            key = _get_api_key()
            from loyan.core.webserv.panel.auth import verify_api_key
            info = verify_api_key(key)
            if info:
                from quart import g
                g.api_key_info = info
                return None
            # 再试JWT
            token = _get_jwt_token()
            from loyan.core.webserv.panel.auth import verify_token
            if token and verify_token(token):
                return None
            from loyan.core.webserv.quart import jsonify
            return jsonify({"message": "unauthorized"}), 401
        
        # 其他路由默认JWT
        token = _get_jwt_token()
        from loyan.core.webserv.panel.auth import verify_token
        if not token or not verify_token(token):
            from loyan.core.webserv.quart import jsonify
            return jsonify({"message": "unauthorized"}), 401

    @app.after_request
    async def no_cache_api(response):
        if _quart_request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
