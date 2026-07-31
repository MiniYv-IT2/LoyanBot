import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

_logger = logging.getLogger("Adapter.Telegram.chat_ops")


async def get_chat_info(bot: Bot, chat_id: int) -> Optional[dict]:
    try:
        chat = await bot.get_chat(chat_id)
        return {
            "id": chat.id,
            "type": chat.type,
            "title": chat.title,
            "username": chat.username,
            "description": chat.description,
            "member_count": chat.get_member_count() if hasattr(chat, "get_member_count") else None,
        }
    except TelegramError:
        return None


async def leave_chat(bot: Bot, chat_id: int) -> bool:
    try:
        await bot.leave_chat(chat_id)
        return True
    except TelegramError:
        return False


async def ban_chat_member(bot: Bot, chat_id: int, user_id: int, revoke_messages: bool = True) -> bool:
    try:
        await bot.ban_chat_member(chat_id, user_id, revoke_messages=revoke_messages)
        return True
    except TelegramError:
        return False


async def unban_chat_member(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        await bot.unban_chat_member(chat_id, user_id)
        return True
    except TelegramError:
        return False


async def restrict_chat_member(
    bot: Bot, chat_id: int, user_id: int,
    until_date: Optional[int] = None,
) -> bool:
    try:
        permissions = {"can_send_messages": False}
        await bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until_date)
        return True
    except TelegramError:
        return False


async def promote_chat_member(
    bot: Bot, chat_id: int, user_id: int,
    can_change_info: bool = False, can_pin_messages: bool = False,
    can_manage_chat: bool = False,
) -> bool:
    try:
        await bot.promote_chat_member(
            chat_id, user_id,
            can_change_info=can_change_info,
            can_pin_messages=can_pin_messages,
            can_manage_chat=can_manage_chat,
        )
        return True
    except TelegramError:
        return False


async def set_chat_title(bot: Bot, chat_id: int, title: str) -> bool:
    try:
        await bot.set_chat_title(chat_id, title)
        return True
    except TelegramError:
        return False


async def set_chat_description(bot: Bot, chat_id: int, description: str) -> bool:
    try:
        await bot.set_chat_description(chat_id, description)
        return True
    except TelegramError:
        return False


async def pin_message(bot: Bot, chat_id: int, message_id: int) -> bool:
    try:
        await bot.pin_chat_message(chat_id, message_id)
        return True
    except TelegramError:
        return False


async def unpin_message(bot: Bot, chat_id: int, message_id: int) -> bool:
    try:
        await bot.unpin_chat_message(chat_id, message_id)
        return True
    except TelegramError:
        return False


async def get_chat_member_count(bot: Bot, chat_id: int) -> int:
    try:
        return await bot.get_chat_member_count(chat_id)
    except TelegramError:
        return 0


async def get_chat_administrators(bot: Bot, chat_id: int) -> list:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return [
            {"user_id": a.user.id, "username": a.user.username, "status": a.status}
            for a in admins
        ]
    except TelegramError:
        return []
