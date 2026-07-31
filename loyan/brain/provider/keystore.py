"""KeyStore — 密钥存储（SQLite + 可选 AES-GCM 加密）"""

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from loyan.core.db_manager import get_db

_logger = logging.getLogger("Brain.keystore")


class KeyStore:
    def __init__(self):
        self._password: str = ""
        self._fernet: Optional[Fernet] = None
        self._db = None

    async def init(self):
        self._db = await get_db("keys")
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS keys (name TEXT PRIMARY KEY, value TEXT)"
        )
        row = await self._db.fetchone("SELECT value FROM keys WHERE name = ?", "_encrypted")
        if row:
            self._password = row[0]

    async def close(self):
        if self._db:
            await self._db.close()

    def set_password(self, password: str):
        self._password = password
        self._fernet = Fernet(self._derive_key(password))
    def disable_encryption(self):
        self._password = ""
        self._fernet = None

    @property
    def is_encrypted(self) -> bool:
        return self._fernet is not None

    def _derive_key(self, password: str) -> bytes:
        salt = hashlib.sha256(password.encode()).digest()
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _encrypt(self, plain: str) -> str:
        if not self._fernet:
            return plain
        return self._fernet.encrypt(plain.encode()).decode()

    def _decrypt(self, cipher: str) -> str:
        if not self._fernet:
            return cipher
        return self._fernet.decrypt(cipher.encode()).decode()

    async def get(self, name: str) -> Optional[str]:
        row = await self._db.fetchone("SELECT value FROM keys WHERE name = ?", name)
        if row is None:
            return None
        return self._decrypt(row[0])

    def encrypt(self, plain: str) -> str:
        """公开加密方法，供外部使用"""
        return self._encrypt(plain)

    def decrypt(self, cipher: str) -> str:
        """公开解密方法，供外部使用"""
        return self._decrypt(cipher)

    async def set(self, name: str, value: str):
        encrypted = self._encrypt(value)
        await self._db.execute(
            "INSERT OR REPLACE INTO keys (name, value) VALUES (?, ?)", name, encrypted
        )

    async def delete(self, name: str):
        await self._db.execute("DELETE FROM keys WHERE name = ?", name)

    async def list_keys(self) -> list[str]:
        rows = await self._db.fetchall("SELECT name FROM keys WHERE name != '_encrypted' ORDER BY name")
        return [row[0] for row in rows]


keystore = KeyStore()
