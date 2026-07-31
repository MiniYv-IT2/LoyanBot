"""QR 服务单元测试 — 加解密 / 二维码构建"""

import base64
import os

import pytest
from Crypto.Cipher import AES

from loyan.core.webserv.panel.service.qr_service import (
    decrypt_secret, generate_bind_key, build_qr_img,
)


class TestGenerateBindKey:
    def test_length(self):
        key = generate_bind_key()
        assert len(base64.b64decode(key)) == 32

    def test_unique(self):
        assert generate_bind_key() != generate_bind_key()


class TestDecryptSecret:
    def _encrypt(self, secret: str, bind_key: str) -> str:
        key = base64.b64decode(bind_key)
        nonce = os.urandom(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ct, tag = cipher.encrypt_and_digest(secret.encode())
        raw = nonce + ct + tag
        return base64.b64encode(raw).decode()

    def test_roundtrip(self):
        bind_key = generate_bind_key()
        secret = "test-app-secret-123"
        encrypted = self._encrypt(secret, bind_key)
        assert decrypt_secret(encrypted, bind_key) == secret

    def test_wrong_key_fails(self):
        bind_key = generate_bind_key()
        wrong_key = generate_bind_key()
        secret = "test-secret"
        encrypted = self._encrypt(secret, bind_key)
        with pytest.raises(Exception):
            decrypt_secret(encrypted, wrong_key)


class TestBuildQrImg:
    def test_contains_task(self):
        url = build_qr_img("task-abc")
        assert "task-abc" in url

    def test_custom_color(self):
        url = build_qr_img("task-abc", color="f0a8c8", bgcolor="1a1a2e")
        assert "color=f0a8c8" in url
        assert "bgcolor=1a1a2e" in url
