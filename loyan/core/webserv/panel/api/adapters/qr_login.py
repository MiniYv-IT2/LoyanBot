"""QQ 扫码登录接口 — create / poll（薄路由，逻辑在 service）"""

from loyan.core.webserv.quart import request

from loyan.core.webserv.panel.service import qr_service


def register_routes(app) -> None:
    @app.route("/api/loyanui/qqbot/qr-login/create", methods=["POST"])
    async def qr_login_create():
        bind_key = qr_service.generate_bind_key()
        try:
            task_id = await qr_service.create_bind_task(bind_key)
        except Exception:
            return {"success": False, "error": "create exception"}, 500
        data = await request.get_json()
        color = (data or {}).get("color", "8ecac8")
        bgcolor = (data or {}).get("bgcolor", "ffffff")
        img_url = qr_service.build_qr_img(task_id, color=color, bgcolor=bgcolor)
        return {"success": True, "data": {"task_id": task_id, "bind_key": bind_key, "qr_img": img_url}}

    @app.route("/api/loyanui/qqbot/qr-login/poll", methods=["POST"])
    async def qr_login_poll():
        data = await request.get_json()
        task_id = data.get("task_id", "")
        bind_key = data.get("bind_key", "")
        if not task_id or not bind_key:
            return {"success": False, "error": "missing params"}, 400
        result = await qr_service.poll_bind_result(task_id, bind_key)
        return {"success": True, "data": result}
