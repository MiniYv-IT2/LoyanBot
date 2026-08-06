"""提供商接口 — CRUD / models / usage"""

from loyan.core.webserv.quart import request


def register_routes(app) -> None:
    @app.route("/api/loyanui/providers/types")
    async def list_provider_types():
        from graci import list_provider_types
        return {"success": True, "data": list_provider_types()}

    @app.route("/api/loyanui/providers/vendors")
    async def list_vendors():
        from graci import list_vendor_types
        return {"success": True, "data": list_vendor_types()}

    @app.route("/api/loyanui/providers", methods=["GET"])
    async def list_instances():
        from graci import list_providers
        instances = await list_providers()
        return {"success": True, "data": instances}

    @app.route("/api/loyanui/providers", methods=["POST"])
    async def add_instance():
        data = await request.get_json()
        if not data or not data.get("id") or not data.get("type"):
            return {"success": False, "message": "id_type_required"}, 400
        from graci import add_provider
        try:
            inst_id = await add_provider(data)
            return {"success": True, "data": {"id": inst_id}}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/<inst_id>", methods=["PUT"])
    async def update_instance(inst_id):
        data = await request.get_json()
        if not data:
            return {"success": False, "message": "empty_body"}, 400
        from graci import update_provider
        try:
            await update_provider(inst_id, data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/<inst_id>", methods=["DELETE"])
    async def delete_instance(inst_id):
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
        from graci import delete_provider
        await delete_provider(inst_id)
        return {"success": True}

    @app.route("/api/loyanui/providers/<inst_id>/models")
    async def list_instance_models(inst_id):
        from graci import list_models
        try:
            models = await list_models(inst_id)
            return {"success": True, "data": models}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/usage")
    async def get_usage():
        from graci import get_usage_summary
        hours = request.args.get("hours", 24, type=int)
        summary = await get_usage_summary(hours=hours)
        return {"success": True, "data": summary}

    @app.route("/api/loyanui/providers/test", methods=["POST"])
    async def test_provider():
        """测试连接：向端点发 /models 请求，验证可达性与 key"""
        import httpx
        data = await request.get_json()
        api_base = (data.get("api_base") or "").strip().rstrip("/")
        api_key = (data.get("api_key") or "").strip()
        if not api_base:
            return {"success": False, "message": "api_base_required"}, 400
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            for path in ("/models", "/v1/models"):
                try:
                    r = await client.get(api_base + path, headers=headers)
                    if r.status_code >= 500:
                        continue
                    models = []
                    if r.status_code == 200:
                        try:
                            models = (r.json().get("data") or [])[:10]
                        except Exception:
                            pass
                    return {
                        "success": r.status_code == 200,
                        "status": r.status_code,
                        "models": [m.get("id") if isinstance(m, dict) else str(m) for m in models],
                        "message": "ok" if r.status_code == 200 else f"HTTP {r.status_code}",
                    }
                except Exception as e:
                    return {"success": False, "message": f"{type(e).__name__}: {str(e)[:120]}"}, 200
        return {"success": False, "message": "unreachable"}, 200
