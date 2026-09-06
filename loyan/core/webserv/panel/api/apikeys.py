"""API Key management - admin only, JWT protected."""

import time
from loyan.core.webserv.quart import request, jsonify


def _require_admin_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = request.args.get("token", "")
    from loyan.core.webserv.panel.auth import verify_token
    if not token or not verify_token(token):
        return None
    return token


def register_routes(app) -> None:
    @app.route("/api/loyanui/apikeys", methods=["GET"])
    async def list_apikeys():
        if not _require_admin_token():
            return jsonify({"message": "unauthorized"}), 401
        from loyan.core.webserv.panel.auth import _get_keys
        return jsonify({"success": True, "data": [
            {"id": k["id"], "name": k["name"], "permissions": k["permissions"],
             "created_at": k["created_at"], "last_used": k.get("last_used", 0)}
            for k in _get_keys()
        ]})

    @app.route("/api/loyanui/apikeys", methods=["POST"])
    async def create_apikey():
        if not _require_admin_token():
            return jsonify({"message": "unauthorized"}), 401
        data = await request.get_json() or {}
        name = (data.get("name") or "").strip()
        perm = data.get("permissions", ["read"])
        if not name:
            return jsonify({"message": "name_required"}), 400
        from loyan.core.webserv.panel.auth import _get_keys, _save_config
        import secrets
        key_value = secrets.token_hex(32)
        key_id = secrets.token_hex(16)
        now = int(time.time())
        entry = {
            "id": key_id,
            "key": key_value,
            "name": name,
            "permissions": sorted(set(perm) & {"read", "write"}),
            "created_at": now,
            "last_used": 0,
        }
        keys = _get_keys()
        keys.append(entry)
        _save_config({"api_keys": keys})
        return jsonify({"success": True, "data": {
            "id": key_id,
            "key": key_value,
            "name": name,
            "permissions": entry["permissions"],
            "created_at": now
        }}), 201

    @app.route("/api/loyanui/apikeys/<key_id>", methods=["DELETE"])
    async def delete_apikey(key_id):
        if not _require_admin_token():
            return jsonify({"message": "unauthorized"}), 401
        from loyan.core.webserv.panel.auth import _get_keys, _save_config
        keys = _get_keys()
        before = len(keys)
        keys = [k for k in keys if k["id"] != key_id]
        if len(keys) < before:
            _save_config({"api_keys": keys})
            return jsonify({"success": True})
        return jsonify({"message": "not_found"}), 404
