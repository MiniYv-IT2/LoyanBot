"""Interface route layer — organized by resource directory."""

from loyan.core.webserv.panel.api import auth
from loyan.core.webserv.panel.api import adapters
from loyan.core.webserv.panel.api import providers
from loyan.core.webserv.panel.api import update
from loyan.core.webserv.panel.api import chat
from loyan.core.webserv.panel.api import monitor
from loyan.core.webserv.panel.api import settings
from loyan.core.webserv.panel.api import plugins
from loyan.core.webserv.panel.api import store
from loyan.core.webserv.panel.api import test
from loyan.core.webserv.panel.api import send
from loyan.core.webserv.panel.api import apikeys


def register_routes(app) -> None:
    auth.register_routes(app)
    adapters.register_routes(app)
    providers.register_routes(app)
    update.register_routes(app)
    chat.register_routes(app)
    monitor.register_routes(app)
    settings.register_routes(app)
    plugins.register_routes(app)
    store.register_routes(app)
    test.register_routes(app)
    send.register_routes(app)
    apikeys.register_routes(app)
