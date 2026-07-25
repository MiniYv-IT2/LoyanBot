"""LoyanUI 前端登录 E2E 测试（Playwright 无头浏览器）"""

import re
from playwright.sync_api import sync_playwright

PANEL_URL = "http://127.0.0.1:5090"


def test_login_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="zh-CN",
        )
        page = context.new_page()

        # 收集前端错误
        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))

        page.goto(PANEL_URL + "/login")
        assert page.locator("h2").text_content() == "LoyanUI"

        # 输入账号密码
        page.fill('input[id="username"]', "Admin")
        page.fill('input[id="password"]', "@Loyan")

        # 等待验证码加载
        page.wait_for_selector("canvas", timeout=5000)

        # 输入验证码（从canvas读不到，但可以故意输错的来测试流程）
        # 实际上这里需要用户输入验证码，但无头模式下看不到
        # 我们先测试验证码输入框存在并且可以交互
        captcha_input = page.locator("input").nth(2)
        assert captcha_input.is_visible()
        captcha_input.fill("TEST")

        # 测试前端页面没有JS错误
        assert len(js_errors) == 0, f"前端JS错误: {js_errors}"

        browser.close()


def test_login_page_renders():
    """测试登录页渲染正常，没有 JS 崩溃"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))

        page.goto(PANEL_URL + "/login")
        page.wait_for_load_state("networkidle")

        # 确认页面渲染正常
        assert page.locator("h2").text_content() == "LoyanUI"
        assert page.locator('img[alt="LoyanUI"]').is_visible()
        assert page.locator("canvas").is_visible()
        btn_text = page.locator("button").first.text_content()
        print(f"\n[DEBUG] 按钮文本: [{btn_text}]")
        assert btn_text.replace(" ", "") in ("登录", "Login", "login.submit"), f"按钮文本异常: {btn_text}"

        # 确认没有 JS 错误
        assert len(js_errors) == 0, f"登录页存在JS错误: {js_errors}"

        browser.close()
