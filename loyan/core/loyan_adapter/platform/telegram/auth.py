import logging
from typing import Optional

_logger = logging.getLogger("Adapter.Telegram.auth")


async def validate_token(token: str, proxy_url: str = "") -> Optional[dict]:
    try:
        from telegram import Bot
        from telegram.request import HTTPXRequest
        kwargs = {}
        if proxy_url:
            kwargs["request"] = HTTPXRequest(proxy=proxy_url, connect_timeout=10)
        bot = Bot(token, **kwargs)
        me = await bot.get_me()
        return {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "is_bot": me.is_bot,
        }
    except Exception as e:
        _logger.error(f"[Telegram] Token 验证失败: {e}")
        return None
