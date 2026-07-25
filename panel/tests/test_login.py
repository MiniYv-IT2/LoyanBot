"""LoyanUI 登录全流程测试"""

import httpx
import logging

PANEL_URL = "http://127.0.0.1:5090"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_login")


def fetch_captcha(client):
    resp = client.get(f"{PANEL_URL}/api/loyanui/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    logger.info(f"Captcha: id={data['data']['id'][:8]}... code={data['data']['code']}")
    return data["data"]["id"], data["data"]["code"]


def test_captcha():
    with httpx.Client() as c:
        captcha_id, captcha_code = fetch_captcha(c)
        assert len(captcha_id) == 32
        assert len(captcha_code) == 4


def test_login_success():
    with httpx.Client() as c:
        captcha_id, captcha_code = fetch_captcha(c)
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        })
        data = resp.json()
        logger.info(f"Login success response: {data}")
        assert resp.status_code == 200
        assert data["success"] is True
        assert "token" in data


def test_login_wrong_password():
    with httpx.Client() as c:
        captcha_id, captcha_code = fetch_captcha(c)
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "wrong_pass",
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        })
        data = resp.json()
        logger.info(f"Wrong password response: {data}")
        assert resp.status_code == 401
        assert data["success"] is False
        assert data["error"] == "login.wrong"


def test_login_wrong_captcha():
    with httpx.Client() as c:
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": "fake_id_123456789012345",
            "captcha_code": "FAKE",
        })
        data = resp.json()
        logger.info(f"Wrong captcha response: {data}")
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"] == "captcha.invalid"


def test_login_missing_captcha():
    with httpx.Client() as c:
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": "",
            "captcha_code": "",
        })
        data = resp.json()
        logger.info(f"Missing captcha response: {data}")
        assert data["success"] is False
        assert data["error"] == "captcha.invalid"


def test_login_empty_captcha_code():
    """模拟前端 captcha_code 为空的情况"""
    with httpx.Client() as c:
        captcha_id, _ = fetch_captcha(c)
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": captcha_id,
            "captcha_code": "",
        })
        data = resp.json()
        logger.info(f"Empty captcha_code response: {data}")
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"] == "captcha.invalid"


def test_login_with_form_values_style():
    """模拟前端从 values.captcha 取验证码的场景"""
    with httpx.Client() as c:
        captcha_id, captcha_code = fetch_captcha(c)
        values_captcha = captcha_code
        resp = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": captcha_id,
            "captcha_code": values_captcha,
        })
        data = resp.json()
        logger.info(f"Form-style login response: {data}")
        assert resp.status_code == 200
        assert data["success"] is True

