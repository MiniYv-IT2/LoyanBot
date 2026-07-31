"""适配器 schema 接口 — 类型/字段定义"""

from loyan.core.tools.schema_i18n import build_schema_response, list_adapter_types


def register_routes(app) -> None:
    @app.route("/api/loyanui/adapter/types")
    async def adapter_types():
        return {"success": True, "data": await list_adapter_types()}

    @app.route("/api/loyanui/adapter/schema/<adapter_type>")
    async def adapter_schema(adapter_type):
        result = await build_schema_response(adapter_type)
        if result is None:
            return {"success": False, "error": "adapter.not_found"}, 404
        return {"success": True, "data": result}
