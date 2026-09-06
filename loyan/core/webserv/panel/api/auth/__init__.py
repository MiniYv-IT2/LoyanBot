"""鉴权接口 — login/captcha/verify/logout/change-account"""

from loyan.core.webserv.quart import request

from loyan.core.webserv.panel.auth import (
    create_token, get_username, verify_password,
    verify_token, generate_captcha, verify_captcha,
    logout, change_account, AccountChangeError, check_permission, verify_api_key,
)


def register_routes(app) -> None:
    @app.route("/api/loyanui/auth/login", methods=["POST"])
    async def login():
        data = await request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")
        captcha_id = data.get("captcha_id", "")
        captcha_code = data.get("captcha_code", "")

        if not verify_captcha(captcha_id, captcha_code):
            return {"success": False, "error": "captcha.invalid"}, 400

        if username == get_username() and verify_password(password):
            token = create_token()
            return {"success": True, "token": token}
        return {"success": False, "error": "login.wrong"}, 401

    @app.route("/api/loyanui/auth/captcha")
    async def captcha():
        captcha_id, code = generate_captcha()
        return {"success": True, "data": {"id": captcha_id, "code": code}}

    @app.route("/api/loyanui/auth/verify")
    async def verify():
        token = request.args.get("token", "")
        if verify_token(token):
            return {"success": True}
        return {"success": False}, 401

    @app.route("/api/loyanui/auth/logout", methods=["POST"])
    async def auth_logout():
        logout()
        return {"success": True, "message": "logged out"}

    @app.route("/api/loyanui/account/change", methods=["POST"])
    async def change_account_route():
        # Require JWT or API Key
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]
            if token and verify_token(token):
                pass
            else:
                return {"success": False, "error": "unauthorized"}, 401
        else:
            key = request.headers.get("X-API-Key", "").strip()
            info = verify_api_key(key)
            if not info:
                return {"success": False, "error": "unauthorized"}, 401

        data = await request.get_json()
        if not data:
            return {"success": False, "error": "empty_body"}, 400

        username = data.get("username")
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        try:
            change_account(username=username, old_password=old_password,
                           new_password=new_password, confirm_password=confirm_password)
        except AccountChangeError as e:
            return {"success": False, "error": str(e)}, 400

        return {"success": True, "message": "account updated"}
