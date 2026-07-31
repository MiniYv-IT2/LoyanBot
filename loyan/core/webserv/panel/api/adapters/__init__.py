"""适配器接口 — 实例 CRUD / reload / rename / schema / 扫码"""

import json
import os
import shutil

from loyan.core.webserv.quart import request

from loyan.core.tools.paths import get_instances_dir
from loyan.core.webserv.panel.service import instance_service
from loyan.core.webserv.panel.api.adapters import schema
from loyan.core.webserv.panel.api.adapters import qr_login

# 敏感字段：GET 掩码返回，PATCH 掩码值不覆盖原值
_MASKED_KEYS = {"app_secret", "secret", "token", "access_token", "appSecret", "clientSecret"}


def _mask_secret(value) -> str:
    """掩码为 前4****后4；短值整体 ****"""
    s = str(value)
    if len(s) <= 8:
        return "****"
    return f"{s[:4]}****{s[-4:]}"


def _is_masked(value) -> bool:
    return isinstance(value, str) and "****" in value


def register_routes(app) -> None:
    @app.route("/api/loyanui/instances", methods=["GET"])
    async def panel_list_instances():
        from loyan.core.loyan_adapter.pool import adapter_pool
        base = get_instances_dir()
        if not os.path.isdir(base):
            return {"success": True, "data": []}
        items = []
        online_names = set()
        for adp, tg in adapter_pool._adapters.values():
            if getattr(adp, "is_connected", True):
                online_names.add(tg.bot_name)
        for name in sorted(os.listdir(base)):
            cfg_path = os.path.join(base, name, "config.json")
            if os.path.isfile(cfg_path):
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                for k in _MASKED_KEYS:
                    if k in cfg and cfg[k]:
                        cfg[k] = _mask_secret(cfg[k])
                cfg["_name"] = name
                status = "offline"
                if not cfg.get("enabled", True):
                    status = "disabled"
                elif name in online_names or cfg.get("bot_name", name) in online_names:
                    status = "online"
                cfg["_status"] = status
                items.append(cfg)
        return {"success": True, "data": items}

    schema.register_routes(app)
    qr_login.register_routes(app)

    @app.route("/api/loyanui/instances", methods=["POST"])
    async def panel_create_instance():
        data = await request.get_json()
        if not data or not data.get("name"):
            return {"success": False, "error": "name_required"}, 400
        name = data.pop("name")
        base = os.path.join(get_instances_dir(), name)
        os.makedirs(base, exist_ok=True)
        cfg_path = os.path.join(base, "config.json")
        data["enabled"] = data.get("enabled", True)
        data["bot_name"] = data.get("bot_name", name)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        result = await instance_service.start_instance(name)
        return {"success": result["success"]}

    @app.route("/api/loyanui/instances/<name>", methods=["PATCH"])
    async def panel_update_instance(name):
        data = await request.get_json()
        if not data:
            return {"success": False, "error": "empty_body"}, 400
        cfg_path = os.path.join(get_instances_dir(), name, "config.json")
        if not os.path.isfile(cfg_path):
            return {"success": False, "error": "not_found"}, 404
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k in _MASKED_KEYS:
            if k in data and _is_masked(data[k]):
                data.pop(k)
        old_bot_name = cfg.get("bot_name", name)
        new_bot_name = data.get("bot_name", old_bot_name)
        cfg.update(data)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        if new_bot_name != name and new_bot_name != old_bot_name:
            result = await instance_service.rename_instance(name, new_bot_name)
            return {"success": result["success"], "renamed": True}
        result = await instance_service.reload_instance(name)
        return {"success": result["success"]}

    @app.route("/api/loyanui/instances/<name>/reload", methods=["POST"])
    async def panel_reload_instance(name):
        return await instance_service.reload_instance(name)

    @app.route("/api/loyanui/instances/<name>/rename", methods=["POST"])
    async def panel_rename_instance(name):
        data = await request.get_json()
        new_name = data.get("new_name", "").strip()
        if not new_name:
            return {"success": False, "error": "new_name_required"}, 400
        return await instance_service.rename_instance(name, new_name)

    @app.route("/api/loyanui/instances/<name>", methods=["DELETE"])
    async def panel_delete_instance(name):
        await instance_service.stop_instance(name)
        data = await request.get_json()
        a = data.get("a", 0)
        b = data.get("b", 0)
        op = data.get("op", "+")
        user_answer = data.get("answer")
        if op == "+":
            expected = a + b
        elif op == "-":
            expected = a - b
        else:
            return {"success": False, "error": "verification_invalid"}, 400
        if user_answer != expected:
            return {"success": False, "error": "verification_wrong"}, 400
        path = os.path.join(get_instances_dir(), name)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return {"success": True}
        return {"success": False, "error": "not_found"}, 404
