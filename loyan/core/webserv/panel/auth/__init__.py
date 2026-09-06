import hashlib
import json
import os
import random
import re
import secrets
import string
import time
from typing import Optional

from loyan.core.tools.paths import get_storage_dir

_CONFIG_FILE = os.path.join(get_storage_dir(), "web_config.json")
_DEFAULT_USERNAME = "Admin"
_DEFAULT_PASSWORD = "@Loyan"
_TOKEN_EXPIRE = 86400
_CAPTCHA_EXPIRE = 300

_tokens: dict[str, float] = {}
_captchas: dict[str, dict] = {}

_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$")


def _load_config() -> dict:
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _ensure_defaults():
    config = _load_config()
    changed = False
    if "port" not in config:
        config["port"] = 5090
        changed = True
    if "username" not in config:
        config["username"] = _DEFAULT_USERNAME
        changed = True
    if "password" not in config:
        config["password"] = _DEFAULT_PASSWORD
        changed = True
    if changed:
        _save_config(config)
    return config


def get_username() -> str:
    config = _ensure_defaults()
    return config.get("username", _DEFAULT_USERNAME)


def verify_password(password: str) -> bool:
    config = _load_config()
    stored = config.get("password", "")
    if not stored:
        config = _ensure_defaults()
        stored = config["password"]

    if stored == _DEFAULT_PASSWORD:
        return password == stored

    salt = config.get("salt", "")
    h = hashlib.md5((password + salt).encode()).hexdigest()
    return h == stored


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not _PASSWORD_RE.match(password):
        return False, "Password must contain uppercase, lowercase, digit and special character"
    return True, ""


def change_password(old_pw: str, new_pw: str) -> bool:
    if not verify_password(old_pw):
        return False
    config = _load_config()
    salt = secrets.token_hex(16)
    h = hashlib.md5((new_pw + salt).encode()).hexdigest()
    config["password"] = h
    config["salt"] = salt
    _save_config(config)
    return True


class AccountChangeError(Exception):
    pass


def change_account(username: Optional[str] = None, old_password: Optional[str] = None,
                   new_password: Optional[str] = None, confirm_password: Optional[str] = None) -> bool:
    """Change account name and/or password.
    At least one of username or new_password must be provided.
    If changing password, old_password and confirm_password are required.
    """
    has_new_username = username is not None and username.strip() != ""
    has_new_password = new_password is not None and new_password.strip() != ""

    if not has_new_username and not has_new_password:
        raise AccountChangeError("At least one of username or password must be changed")

    current_username = get_username()

    if has_new_username:
        username = username.strip()
        if len(username) < 5:
            raise AccountChangeError("Username must be at least 5 characters")
        config = _load_config()
        config["username"] = username
        _save_config(config)

    if has_new_password:
        if not old_password:
            raise AccountChangeError("Old password is required to change password")
        if not verify_password(old_password):
            raise AccountChangeError("Old password is incorrect")
        if new_password != confirm_password:
            raise AccountChangeError("New password and confirmation do not match")
        # Factory default password is exempt from strength requirements
        if new_password != _DEFAULT_PASSWORD:
            ok, msg = validate_password(new_password)
            if not ok:
                raise AccountChangeError(msg)
        config = _load_config()
        if new_password == _DEFAULT_PASSWORD:
            # Restore to plain-text default
            config["password"] = _DEFAULT_PASSWORD
            if "salt" in config:
                del config["salt"]
        else:
            salt = secrets.token_hex(16)
            h = hashlib.md5((new_password + salt).encode()).hexdigest()
            config["password"] = h
            config["salt"] = salt
        _save_config(config)

    return True


def logout() -> bool:
    """Invalidate all active tokens."""
    global _tokens
    count = len(_tokens)
    _tokens.clear()
    return count > 0


def get_panel_settings() -> dict:
    """面板设置（不回密码）"""
    config = _ensure_defaults()
    return {k: config.get(k) for k in ("username", "port", "ssl_enable", "ssl_cert", "ssl_key")}


def save_panel_settings(data: dict, old_password: str = "", new_password: str = "") -> tuple[bool, str]:
    """保存面板设置；提供新旧密码时改密"""
    config = _ensure_defaults()
    for key in ("username", "port", "ssl_enable", "ssl_cert", "ssl_key"):
        if key in data:
            config[key] = data[key]
    if new_password:
        if not verify_password(old_password):
            return False, "旧密码错误"
        ok, msg = validate_password(new_password)
        if not ok:
            return False, msg
        salt = secrets.token_hex(16)
        h = hashlib.md5((new_password + salt).encode()).hexdigest()
        config["password"] = h
        config["salt"] = salt
    _save_config(config)
    return True, ""


def create_token() -> str:
    token = secrets.token_hex(32)
    _tokens[token] = time.time() + _TOKEN_EXPIRE
    return token


def verify_token(token: str) -> bool:
    exp = _tokens.get(token)
    if exp is None:
        return False
    if time.time() > exp:
        del _tokens[token]
        return False
    return True


def get_port() -> int:
    config = _ensure_defaults()
    return config.get("port", 5090)


def generate_captcha() -> tuple[str, str]:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    captcha_id = secrets.token_hex(16)
    _captchas[captcha_id] = {
        "code": code,
        "expire": time.time() + _CAPTCHA_EXPIRE,
    }
    return captcha_id, code


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    data = _captchas.get(captcha_id)
    if not data:
        return False
    if time.time() > data["expire"]:
        del _captchas[captcha_id]
        return False
    del _captchas[captcha_id]
    return data["code"].upper() == captcha_code.upper()


# ── API Key 认证（只读验证，管理需手动编辑 web_config.json）──

def _get_keys() -> list[dict]:
    config = _load_config()
    return config.get("api_keys", [])


def verify_api_key(raw_key: str) -> Optional[dict]:
    """验证 API Key，返回权限信息"""
    if not raw_key or len(raw_key) != 64:
        return None
    now = int(time.time())
    for k in _get_keys():
        if k["key"] == raw_key:
            k["last_used"] = now
            # 更新存储
            config = _load_config()
            config["api_keys"] = _get_keys()
            _save_config(config)
            return {"id": k["id"], "permissions": k["permissions"], "last_used": now}
    return None


def check_permission(permissions: list[str], required: str) -> bool:
    """检查权限"""
    if required == "read":
        return True
    return "write" in set(permissions)
