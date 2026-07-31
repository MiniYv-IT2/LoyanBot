"""监控接口 — stats / health / metrics / status"""

from datetime import datetime

from loyan.core.webserv.quart import request, jsonify


def register_routes(app) -> None:
    @app.route("/api/loyanui/version")
    async def version():
        from loyan.core.config import BOT_VERSION
        return {"success": True, "data": {"version": BOT_VERSION}}

    @app.route("/api/loyanui/stats")
    async def stats():
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            from loyan.core.pipeline.stats_collector import stats_collector
            msg_stats = await stats_collector.get_stats(since=today_start)

            from loyan.core.plugin_manager import plugin_manager
            plugins = plugin_manager.get_plugin_count()

            from loyan.core.decorators.registration import DECORATOR_COMMAND_REGISTRY
            plugin_cmds = sum(len(p.get("commands", [])) for p in plugin_manager.registry)
            decorator_cmds = sum(len(e.get("commands", [])) for e in DECORATOR_COMMAND_REGISTRY)
            builtin_cmds = 4  # /关机 /重启 /开机 /关于
            total_commands = plugin_cmds + decorator_cmds + builtin_cmds

            uptime = 0.0
            try:
                from loyan.core.monitor import monitor_manager
                status = monitor_manager.get_system_status()
                uptime = status.get("uptime_seconds", 0)
            except Exception:
                from loyan.core.lifecycle.state.state_machine import lifecycle_state_machine
                uptime = lifecycle_state_machine.uptime

            return {
                "success": True,
                "data": {
                    "total_messages": msg_stats.get("total_messages", 0),
                    "total_commands": total_commands,
                    "uptime_seconds": uptime,
                    "plugins": plugins,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @app.route("/health", methods=["GET"])
    async def health_check():
        from loyan.core.monitor import monitor_manager
        health_info = monitor_manager.get_health_check()
        status_code = 200 if health_info["status"] == "healthy" else 503
        return jsonify(health_info), status_code

    @app.route("/metrics", methods=["GET"])
    async def get_metrics():
        from loyan.core.monitor import monitor_manager
        metrics = monitor_manager.get_performance_metrics()
        return jsonify(metrics)

    @app.route("/status", methods=["GET"])
    async def get_status():
        from loyan.core.monitor import monitor_manager
        status = monitor_manager.get_system_status()
        return jsonify(status)
