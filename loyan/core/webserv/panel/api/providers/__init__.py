"""提供商接口 — CRUD / models / usage"""

from loyan.core.webserv.quart import request


def register_routes(app) -> None:
    @app.route("/api/loyanui/providers/types")
    async def list_provider_types():
        from graci import list_provider_types
        return {"success": True, "data": list_provider_types()}

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
