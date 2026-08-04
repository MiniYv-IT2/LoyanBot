"""插件商店接口 — 列表 / 安装 / 更新 / 点赞 / 配置"""

import inspect

from loyan.core.webserv.quart import request

try:
    from loyan.core.plugin_store import plugin_store
except Exception:
    plugin_store = None

try:
    from loyan.core.plugin_stats import plugin_stats
except Exception:
    plugin_stats = None


async def _call(fn, *args):
    result = fn(*args)
    if inspect.iscoroutine(result):
        return await result
    return result


async def _get_data(fn, *args):
    if fn is None:
        return {"success": False, "message": "not_ready"}, 503
    try:
        return {"success": True, "data": await _call(fn, *args)}
    except Exception as e:
        return {"success": False, "message": str(e)}, 400


async def _run_action(fn, *args):
    if fn is None:
        return {"success": False, "message": "not_ready"}, 503
    try:
        await _call(fn, *args)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}, 400


def register_routes(app) -> None:
    @app.route("/api/loyanui/store/plugins")
    async def store_plugins():
        force = request.args.get("force", "0") == "1"
        return await _get_data(plugin_store.store_list if plugin_store else None, force)

    @app.route("/api/loyanui/store/plugins/<id>/install", methods=["POST"])
    async def install_plugin(id):
        if not id or "/" in id:
            return {"success": False, "message": "invalid_id"}, 400
        return await _run_action(plugin_store.store_install if plugin_store else None, id)

    @app.route("/api/loyanui/store/plugins/<id>/update", methods=["POST"])
    async def update_plugin(id):
        if not id or "/" in id:
            return {"success": False, "message": "invalid_id"}, 400
        return await _run_action(plugin_store.store_update if plugin_store else None, id)

    @app.route("/api/loyanui/store/plugins/<id>/like", methods=["POST"])
    async def like_plugin(id):
        if not id or "/" in id:
            return {"success": False, "message": "invalid_id"}, 400
        return await _run_action(plugin_stats.store_like if plugin_stats else None, id)

    @app.route("/api/loyanui/store/config")
    async def get_store_config():
        return await _get_data(plugin_store.get_config if plugin_store else None)

    @app.route("/api/loyanui/store/config", methods=["PUT"])
    async def put_store_config():
        data = await request.get_json()
        if not isinstance(data, dict):
            return {"success": False, "message": "body_required"}, 400
        return await _run_action(plugin_store.save_config if plugin_store else None, data)
