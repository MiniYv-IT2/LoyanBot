import asyncio
import logging
from typing import List

from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError

from loyan.core.loyan_adapter.message import (
    LoyanMsg, LoyanText, LoyanImage, LoyanVoice, LoyanFile, LoyanVideo,
)

_logger = logging.getLogger("Adapter.Telegram.sender")
_TG_MSG_LIMIT = 4096
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0


def _resolve(segments):
    text = ""
    photo = video = audio = document = None
    for seg in segments:
        if isinstance(seg, LoyanText):
            text += seg.text
        elif isinstance(seg, LoyanImage):
            photo = seg.file_path or seg.url or seg.file_data or None
        elif isinstance(seg, LoyanVideo):
            video = seg.file_path or seg.url or seg.file_data or None
        elif isinstance(seg, LoyanVoice):
            audio = seg.file_path or None
        elif isinstance(seg, LoyanFile):
            document = seg.file_path or seg.url or None
    return text, photo, video, audio, document


async def send_chat_action(bot, chat_id, action=ChatAction.TYPING):
    try:
        await bot.send_chat_action(chat_id=chat_id, action=action)
    except TelegramError:
        pass


async def send_split_text(bot, chat_id, text):
    if len(text) <= _TG_MSG_LIMIT:
        await bot.send_message(chat_id=chat_id, text=text)
        return
    for i in range(0, len(text), _TG_MSG_LIMIT):
        chunk = text[i:i + _TG_MSG_LIMIT]
        await bot.send_message(chat_id=chat_id, text=chunk)
        await asyncio.sleep(0.05)


async def send_media_group(bot, chat_id, segments, caption=""):
    media = []
    for seg in segments:
        if isinstance(seg, LoyanImage):
            src = seg.file_path or seg.url or seg.file_data
            if src:
                media.append(InputMediaPhoto(media=src))
        elif isinstance(seg, LoyanVideo):
            src = seg.file_path or seg.url or seg.file_data
            if src:
                media.append(InputMediaVideo(media=src))
    if not media:
        return
    if caption:
        media[0].caption = caption
    await bot.send_media_group(chat_id=chat_id, media=media[:10])


async def send_dice(bot, chat_id, emoji="🎲"):
    await bot.send_dice(chat_id=chat_id, emoji=emoji)


async def send_sticker(bot, chat_id, sticker):
    await bot.send_sticker(chat_id=chat_id, sticker=sticker)


async def send_poll(bot, chat_id, question, options, is_anonymous=True, allows_multiple_answers=False):
    await bot.send_poll(
        chat_id=chat_id, question=question,
        options=options, is_anonymous=is_anonymous,
        allows_multiple_answers=allows_multiple_answers,
    )


async def edit_message_text(bot, chat_id, message_id, text, parse_mode=None):
    await bot.edit_message_text(
        chat_id=chat_id, message_id=int(message_id),
        text=text, parse_mode=parse_mode,
    )


async def delete_message(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=int(message_id))
    except TelegramError:
        pass


async def forward_message(bot, chat_id, from_chat_id, message_id):
    await bot.forward_message(
        chat_id=chat_id,
        from_chat_id=int(from_chat_id),
        message_id=int(message_id),
    )


async def copy_message(bot, chat_id, from_chat_id, message_id, caption=None):
    await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=int(from_chat_id),
        message_id=int(message_id),
        caption=caption,
    )


async def send_message(bot, target_id, segments, chat_type):
    try:
        chat_id = int(target_id)
    except (ValueError, TypeError):
        return False
    text, photo, video, audio, document = _resolve(segments)
    caption = text or None
    for attempt in range(_MAX_RETRIES):
        try:
            if photo:
                await send_chat_action(bot, chat_id, ChatAction.UPLOAD_PHOTO)
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            elif video:
                await send_chat_action(bot, chat_id, ChatAction.UPLOAD_VIDEO)
                await bot.send_video(chat_id=chat_id, video=video, caption=caption)
            elif audio:
                await send_chat_action(bot, chat_id, ChatAction.UPLOAD_VOICE)
                await bot.send_audio(chat_id=chat_id, audio=audio, caption=caption)
            elif document:
                await send_chat_action(bot, chat_id, ChatAction.UPLOAD_DOCUMENT)
                await bot.send_document(chat_id=chat_id, document=document, caption=caption)
            else:
                await send_chat_action(bot, chat_id, ChatAction.TYPING)
                await send_split_text(bot, chat_id, text or " ")
            return True
        except TelegramError as e:
            if "429" in str(e):
                await asyncio.sleep(_RETRY_DELAY * (2 ** attempt))
                continue
            if attempt == _MAX_RETRIES - 1:
                return False
            await asyncio.sleep(_RETRY_DELAY)
    return False
