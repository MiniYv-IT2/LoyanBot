"""面板域 — Web 可视化机器人管理

结构：
  server.py    核心服务：启动/端口/重试
  static.py    核心服务：静态文件
  commands.py  核心服务：/panel 聊天命令
  auth/        鉴权（token/密码/验证码）
  api/         路由层（收参/校验/返回）
  service/     业务层（逻辑/编排/解密）
"""

from loyan.core.webserv.quart import Quart

from loyan.core.webserv.panel.api import register_routes as _api_register
from loyan.core.webserv.panel.static import register_routes as _static_register


def create_panel_app() -> Quart:
    app = Quart("LoyanUI")
    _api_register(app)
    _static_register(app)

    @app.after_request
    async def no_cache_api(response):
        from loyan.core.webserv.quart import request
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
