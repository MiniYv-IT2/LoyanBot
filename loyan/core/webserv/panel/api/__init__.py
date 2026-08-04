"""接口路由层 — 按资源分目录"""

from loyan.core.webserv.panel.api import auth
from loyan.core.webserv.panel.api import adapters
from loyan.core.webserv.panel.api import providers
from loyan.core.webserv.panel.api import monitor
from loyan.core.webserv.panel.api import settings
from loyan.core.webserv.panel.api import plugins
from loyan.core.webserv.panel.api import store


def register_routes(app) -> None:
    auth.register_routes(app)
    adapters.register_routes(app)
    providers.register_routes(app)
    monitor.register_routes(app)
    settings.register_routes(app)
    plugins.register_routes(app)
    store.register_routes(app)
