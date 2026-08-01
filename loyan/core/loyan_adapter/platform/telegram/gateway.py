import asyncio
import logging
from typing import Callable, Optional

from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder, Application, MessageHandler, CommandHandler,
    CallbackQueryHandler, InlineQueryHandler, ChosenInlineResultHandler,
    ChatMemberHandler, PollAnswerHandler, PreCheckoutQueryHandler,
    ShippingQueryHandler, filters, CallbackContext,
)

from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from .protocol import update_to_loyan

_logger = logging.getLogger("Adapter.Telegram.gateway")


class TelegramGateway:
    def __init__(
        self,
        token: str,
        on_event: Callable[[LoyanEvent], None],
        tag: IdentityTag,
        webhook_url: Optional[str] = None,
        webhook_port: int = 8443,
        proxy_url: Optional[str] = None,
        parse_business: Optional[Callable] = None,
    ):
        self._token = token
        self._proxy_url = proxy_url
        self._on_event = on_event
        self._tag = tag
        self._webhook_url = webhook_url
        self._webhook_port = webhook_port
        self._proxy_url = proxy_url
        self._parse_business = parse_business
        self._app: Optional[Application] = None
        self._running = False
        self._reconnect_delay = 1

    async def start(self):
        self._running = True
        from telegram import Bot
        from telegram.request import HTTPXRequest
        bot_kwargs = {}
        if self._proxy_url:
            req = HTTPXRequest(proxy=self._proxy_url, connect_timeout=15, pool_timeout=15)
            get_req = HTTPXRequest(proxy=self._proxy_url, connect_timeout=15, pool_timeout=15)
            bot_kwargs["request"] = req
            bot_kwargs["get_updates_request"] = get_req
        bot = Bot(self._token, **bot_kwargs)
        self._app = ApplicationBuilder().bot(bot).build()
        self._app.add_handler(MessageHandler(filters.ALL, self._handle_message))
        self._app.add_handler(CommandHandler("_tg_catch_all", self._handle_message))
        self._app.add_handler(CallbackQueryHandler(self._handle_update))
        self._app.add_handler(InlineQueryHandler(self._handle_update))
        self._app.add_handler(ChosenInlineResultHandler(self._handle_update))
        self._app.add_handler(ChatMemberHandler(self._handle_update, chat_member_types=0))
        self._app.add_handler(PollAnswerHandler(self._handle_update))
        self._app.add_handler(PreCheckoutQueryHandler(self._handle_update))
        self._app.add_handler(ShippingQueryHandler(self._handle_update))
        self._app.add_error_handler(self._handle_error)
        await self._app.initialize()
        await self._app.start()
        if self._webhook_url:
            await self._app.bot.set_webhook(
                url=self._webhook_url,
                allowed_updates=Update.ALL_TYPES,
                max_connections=40,
            )
        else:
            await self._app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                error_callback=self._polling_error,
            )

    async def stop(self):
        self._running = False
        if not self._app:
            return
        try:
            if self._webhook_url:
                await self._app.bot.delete_webhook(drop_pending_updates=True)
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        except Exception:
            pass

    async def restart(self):
        await self.stop()
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, 30)
        await self.start()

    async def _handle_message(self, update: Update, context: CallbackContext):
        await self._async_handle(update, context)

    async def _handle_update(self, update: Update, context: CallbackContext):
        await self._async_handle(update, context)

    async def _async_handle(self, update: Update, context: CallbackContext):
        if not self._running:
            return
        try:
            event = update_to_loyan(update, self._tag)
            if event and self._on_event:
                await self._on_event(event)
            # 业务事件（进群/退群/禁言等）与消息事件并行发布
            if self._parse_business:
                biz = self._parse_business(update)
                if biz is not None:
                    await self._publish_business(biz)
        except ValueError:
            pass
        except Exception:
            _logger.error(f"[Telegram] 处理异常", exc_info=True)

    async def _publish_business(self, biz) -> None:
        """发布业务事件到 EventBus（总线未就绪时静默跳过）"""
        try:
            from loyan.core.event import event_bus
            publish = getattr(event_bus, "publish_business", None)
            if publish is not None:
                await publish(biz)
        except Exception:
            pass

    async def _handle_error(self, update: Update, context: CallbackContext):
        _logger.error(f"[Telegram] 更新处理异常: {context.error}", exc_info=True)

    def _polling_error(self, error: Exception):
        _logger.error(f"[Telegram] 轮询异常: {error}")
