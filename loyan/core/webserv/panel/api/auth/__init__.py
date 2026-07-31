"""鉴权接口 — login/captcha/verify"""

from loyan.core.webserv.quart import request

from loyan.core.webserv.panel.auth import (
    create_token, get_username, verify_password,
    verify_token, generate_captcha, verify_captcha,
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
