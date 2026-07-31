"""面板静态文件服务 — panel-dist"""

import os

from loyan.core.webserv.quart import send_from_directory

PANEL_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "panel-dist",
)


def register_routes(app) -> None:
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    async def serve_panel(path):
        if not path:
            return await send_from_directory(PANEL_DIST, "index.html")
        file_path = os.path.join(PANEL_DIST, path)
        if os.path.exists(file_path):
            return await send_from_directory(PANEL_DIST, path)
        return await send_from_directory(PANEL_DIST, "index.html")
