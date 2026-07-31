"""QQ 扫码业务 — create_bind_task / poll / AES 解密"""

import base64
import logging
import secrets
import traceback

import httpx
from Crypto.Cipher import AES

_logger = logging.getLogger("Panel.qr_service")

_BIND_HOST = "q.qq.com"
_QR_BG_DEFAULT = "ffffff"
_QR_COLOR_DEFAULT = "8ecac8"


def generate_bind_key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def decrypt_secret(encrypted_secret: str, bind_key: str) -> str:
    key = base64.b64decode(bind_key)
    raw = base64.b64decode(encrypted_secret)
    nonce, tag, ct = raw[:12], raw[-16:], raw[12:-16]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ct, tag).decode("utf-8")


async def create_bind_task(bind_key: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://{_BIND_HOST}/lite/create_bind_task",
            json={"key": bind_key},
        )
        data = resp.json()
    if data.get("retcode") != 0:
        raise RuntimeError(data.get("msg", "create_bind_task failed"))
    task_id = str(data.get("data", {}).get("task_id", ""))
    if not task_id:
        raise RuntimeError("create_bind_task: missing task_id")
    return task_id


def build_qr_img(task_id: str, color: str = _QR_COLOR_DEFAULT, bgcolor: str = _QR_BG_DEFAULT) -> str:
    qr_url = f"https://{_BIND_HOST}/qqbot/openclaw/connect.html?task_id={task_id}&_wv=2"
    return (
        f"https://api.qrserver.com/v1/create-qr-code/?size=300x300"
        f"&data={qr_url}&color={color}&bgcolor={bgcolor}"
    )


async def poll_bind_result(task_id: str, bind_key: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://{_BIND_HOST}/lite/poll_bind_result",
            json={"task_id": task_id},
        )
        data = resp.json()
    if data.get("retcode") != 0:
        return {"status": "error", "message": data.get("msg", "poll failed")}
    payload = data.get("data", {})
    status = int(payload.get("status", 0))
    if status == 2:
        appid = str(payload.get("bot_appid", "")).strip()
        encrypted = str(payload.get("bot_encrypt_secret", "")).strip()
        if not appid or not encrypted:
            return {"status": "error", "message": "missing credentials"}
        try:
            secret = decrypt_secret(encrypted, bind_key)
        except Exception:
            _logger.error("QR decrypt failed: %s", traceback.format_exc())
            return {"status": "error", "message": "decrypt failed"}
        return {"status": "scanned", "appid": appid, "secret": secret}
    elif status == 3:
        return {"status": "expired"}
    return {"status": "pending"}
