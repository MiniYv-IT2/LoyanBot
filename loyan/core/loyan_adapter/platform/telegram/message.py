import logging
from typing import List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from loyan.core.loyan_adapter.message import (
    LoyanMsg, LoyanText, LoyanImage, LoyanVoice,
    LoyanFile, LoyanVideo, LoyanAt, LoyanReply,
)

_logger = logging.getLogger("Adapter.Telegram.message")


def build_send_kwargs(segments: List[LoyanMsg]) -> Tuple[str, dict]:
    text_parts = []
    media = None
    media_type = None

    for seg in segments:
        if isinstance(seg, LoyanText):
            text_parts.append(seg.text)
        elif isinstance(seg, LoyanImage):
            media = seg.file_path or seg.url or seg.file_data or None
            media_type = "photo"
        elif isinstance(seg, LoyanVideo):
            media = seg.file_path or seg.url or seg.file_data or None
            media_type = "video"
        elif isinstance(seg, LoyanVoice):
            media = seg.file_path or None
            media_type = "audio"
        elif isinstance(seg, LoyanFile):
            media = seg.file_path or seg.url or None
            media_type = "document"
        elif isinstance(seg, LoyanAt):
            if seg.target_id:
                text_parts.append(f"@{seg.target_id}")

    caption = "".join(text_parts).strip() if text_parts else ""

    if media_type:
        kwargs = {"caption": caption or None}
        if media_type == "photo":
            return "photo", {**kwargs, "photo": media}
        elif media_type == "video":
            return "video", {**kwargs, "video": media}
        elif media_type == "audio":
            return "audio", {**kwargs, "audio": media}
        elif media_type == "document":
            return "document", {**kwargs, "document": media}

    return "text", {"text": caption or " "}


def build_inline_keyboard(buttons: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
    keyboard = []
    for row in buttons:
        keyboard.append([
            InlineKeyboardButton(text=label, callback_data=data)
            for label, data in row
        ])
    return InlineKeyboardMarkup(keyboard)


def detect_parse_mode(text: str) -> Optional[str]:
    if "```" in text or "```python" in text or "`" in text:
        return ParseMode.MARKDOWN
    if "<b>" in text or "<i>" in text or "<code>" in text or "<a href=" in text:
        return ParseMode.HTML
    return None
