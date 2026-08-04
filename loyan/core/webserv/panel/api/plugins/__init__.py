"""插件管理接口 — 列表 / 启用 / 禁用 / 重载"""

import inspect

try:
    from loyan.core.plugin_manager import plugin_manager
except Exception:
    plugin_manager = None


async def _call(fn, *args):
    result = fn(*args)
    if inspect.iscoroutine(result):
        return await result
    return result


async def _run_action(name, method):
    if plugin_manager is None:
        return {"success": False, "message": "not_ready"}, 503
    if not name or "/" in name:
        return {"success": False, "message": "invalid_name"}, 400
    try:
        result = await _call(getattr(plugin_manager, method), name)
        if result is False:
            return {"success": False, "message": "plugin_not_found"}, 404
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}, 400


def register_routes(app) -> None:
    @app.route("/api/loyanui/plugins")
    async def list_plugins():
        if plugin_manager is None:
            return {"success": False, "message": "not_ready"}, 503
        try:
            data = await _call(plugin_manager.list_plugins)
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/plugins/<name>/enable", methods=["POST"])
    async def enable_plugin(name):
        return await _run_action(name, "enable_plugin")

    @app.route("/api/loyanui/plugins/<name>/disable", methods=["POST"])
    async def disable_plugin(name):
        return await _run_action(name, "disable_plugin")

    @app.route("/api/loyanui/plugins/<name>/reload", methods=["POST"])
    async def reload_plugin(name):
        return await _run_action(name, "reload_plugin")
