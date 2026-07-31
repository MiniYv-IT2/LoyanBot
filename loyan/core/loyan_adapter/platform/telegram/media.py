import logging
import os
from pathlib import Path
from typing import Optional

from telegram import Bot

_logger = logging.getLogger("Adapter.Telegram.media")

_FILE_SIZE_LIMIT = 50 * 1024 * 1024
_THUMB_SIZE_LIMIT = 200 * 1024
_THUMB_MAX_WH = 320

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
_DOC_EXT = {".pdf", ".doc", ".docx", ".zip", ".txt", ".csv", ".xlsx", ".pptx"}


def guess_media_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _IMAGE_EXT:
        return "photo"
    if ext in _VIDEO_EXT:
        return "video"
    if ext in _AUDIO_EXT:
        return "audio"
    return "document"


def validate_file_size(file_path):
    try:
        return os.path.getsize(file_path) <= _FILE_SIZE_LIMIT
    except OSError:
        return False


def validate_thumbnail(file_path):
    try:
        size = os.path.getsize(file_path)
        if size > _THUMB_SIZE_LIMIT:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in {".jpg", ".jpeg"}
    except OSError:
        return False


def prepare_upload(file_path="", file_bytes=None, file_url=""):
    if file_url:
        return file_url, None
    if file_bytes:
        if len(file_bytes) > _FILE_SIZE_LIMIT:
            return None, None
        return file_bytes, "file.bin"
    if file_path:
        p = Path(file_path)
        if p.exists():
            if not validate_file_size(str(p)):
                return None, None
            return open(str(p), "rb"), p.name
    return None, None


async def download_file(bot, file_id, timeout=30):
    try:
        f = await bot.get_file(file_id, timeout=timeout)
        return await f.download_as_bytearray()
    except Exception:
        return None


async def get_file_info(bot, file_id):
    try:
        f = await bot.get_file(file_id)
        return {"file_id": f.file_id, "file_size": f.file_size, "file_path": f.file_path}
    except Exception:
        return None
