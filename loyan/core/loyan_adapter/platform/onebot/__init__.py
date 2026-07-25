"""OneBot 平台适配器

遵循 OneBot 11 标准，支持 NapCat 等兼容客户端。
"""

from loyan.core.loyan_adapter.platform.onebot.http import LoyanOneBot
from loyan.core.loyan_adapter.platform.onebot.ws import LoyanOneBotWS

__all__ = [
    "LoyanOneBot",
    "LoyanOneBotWS",
]
