"""系统设置接口 — schema / 读取 / 保存 / 用户配置"""

from loyan.core.webserv.quart import request


def register_routes(app) -> None:
    @app.route("/api/loyanui/settings/schema")
    async def settings_schema():
        from loyan.core.tools.schema_i18n import build_schema_response
        result = await build_schema_response("settings")
        if result is None:
            return {"success": False, "error": "settings.schema_not_found"}, 404
        return {"success": True, "data": result}

    @app.route("/api/loyanui/settings", methods=["GET"])
    async def get_settings():
        from loyan.core.config_manager import config_manager
        values = {key: config_manager.get(key) for key in config_manager.list_keys()}
        return {"success": True, "data": values}

    @app.route("/api/loyanui/settings", methods=["PUT"])
    async def update_settings():
        data = await request.get_json()
        if not data:
            return {"success": False, "message": "empty_body"}, 400
        from loyan.core.config_manager import config_manager
        for key, value in data.items():
            if not config_manager.set(key, value):
                return {"success": False, "message": f"invalid_value: {key}"}, 400
        config_manager.save_to_file()
        return {"success": True}

    # ── 用户配置（全局默认 + 实例覆盖） ──

    @app.route("/api/loyanui/user-config/schema")
    async def user_config_schema():
        from loyan.core.tools.schema_i18n import build_schema_response
        result = await build_schema_response("user_config")
        if result is None:
            return {"success": False, "error": "user_config.schema_not_found"}, 404
        return {"success": True, "data": result}

    @app.route("/api/loyanui/user-config", methods=["GET"])
    async def get_user_config():
        from loyan.core.config.user_config import get_global, get_instance, get_effective
        instance = request.args.get("instance", "")
        if instance:
            return {"success": True, "data": {
                "global": get_global(),
                "instance": get_instance(instance),
                "effective": get_effective(instance),
            }}
        return {"success": True, "data": get_global()}

    @app.route("/api/loyanui/user-config", methods=["PUT"])
    async def update_user_config():
        data = await request.get_json()
        if not data or "data" not in data:
            return {"success": False, "message": "empty_body"}, 400
        from loyan.core.config.user_config import save_global, save_instance
        if data.get("scope", "global") == "instance":
            instance = data.get("instance", "")
            if not instance:
                return {"success": False, "message": "instance_required"}, 400
            save_instance(instance, data["data"])
        else:
            save_global(data["data"])
        return {"success": True}

    # ── 面板设置 ──

    @app.route("/api/loyanui/panel/schema")
    async def panel_schema():
        from loyan.core.tools.schema_i18n import build_schema_response
        result = await build_schema_response("panel")
        if result is None:
            return {"success": False, "error": "panel.schema_not_found"}, 404
        return {"success": True, "data": result}

    @app.route("/api/loyanui/panel", methods=["GET"])
    async def get_panel_settings():
        from loyan.core.webserv.panel.auth import get_panel_settings as _gps
        return {"success": True, "data": _gps()}

    @app.route("/api/loyanui/panel", methods=["PUT"])
    async def update_panel_settings():
        data = await request.get_json()
        if not data:
            return {"success": False, "message": "empty_body"}, 400
        from loyan.core.webserv.panel.auth import save_panel_settings as _sps
        ok, msg = _sps(data, data.get("old_password", ""), data.get("new_password", ""))
        if not ok:
            return {"success": False, "message": msg}, 400
        return {"success": True}
