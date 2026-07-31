"""鉴权逻辑单元测试 — token / 验证码"""

from loyan.core.webserv.panel import auth as panel_auth


class TestToken:
    def test_create_and_verify(self):
        token = panel_auth.create_token()
        assert panel_auth.verify_token(token) is True

    def test_invalid_token(self):
        assert panel_auth.verify_token("invalid-token") is False


class TestCaptcha:
    def test_generate_and_verify(self):
        captcha_id, code = panel_auth.generate_captcha()
        assert panel_auth.verify_captcha(captcha_id, code) is True

    def test_wrong_code(self):
        captcha_id, code = panel_auth.generate_captcha()
        assert panel_auth.verify_captcha(captcha_id, "0000") is False

    def test_invalid_id(self):
        assert panel_auth.verify_captcha("no-such-id", "1234") is False
