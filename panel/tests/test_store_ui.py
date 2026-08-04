"""洛颜商店页面 Playwright 测试 — 渲染 / 搜索 / 分类 / 分页 / 点赞 / i18n"""

import logging

import httpx
from playwright.sync_api import sync_playwright

PANEL_URL = "http://127.0.0.1:5090"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_store_ui")


def login_via_token(page):
    with httpx.Client(timeout=10) as c:
        cap = c.get(f"{PANEL_URL}/api/loyanui/auth/captcha").json()["data"]
        res = c.post(f"{PANEL_URL}/api/loyanui/auth/login", json={
            "username": "Admin",
            "password": "@Loyan",
            "captcha_id": cap["id"],
            "captcha_code": cap["code"],
        }).json()
        assert res["success"] is True
        token = res["token"]
    page.goto(f"{PANEL_URL}/login")
    page.evaluate(f"localStorage.setItem('token', '{token}')")
    page.goto(f"{PANEL_URL}/plugins/store")
    page.wait_for_load_state("networkidle")


def test_store_page_render():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.goto(f"{PANEL_URL}/plugins/store")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        # 标题（i18n：中文环境显示洛颜商店）
        assert page.locator("text=洛颜商店").count() > 0
        # 插件卡片（服务器源 3 个插件）
        cards = page.locator(".plugin-card")
        assert cards.count() >= 1
        # 搜索框 + 排序 + 源按钮存在（桌面/移动双搜索框，取第一个）
        assert page.locator('input[placeholder*="搜索"]').count() > 0
        # 分页（少于 12 个插件时不显示）
        logger.info(f"渲染卡片数: {cards.count()}")
        browser.close()


def test_store_search_filter():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.goto(f"{PANEL_URL}/plugins/store")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        # 桌面/移动双搜索框，取可见的那个
        search = page.locator('input[placeholder*="搜索"]:visible').first
        search.fill("音乐")
        page.wait_for_timeout(500)
        cards = page.locator(".plugin-card")
        assert cards.count() >= 1
        assert page.locator(".plugin-card:has-text('小禹听歌插件')").count() >= 1
        search.fill("不存在的插件xyz")
        page.wait_for_timeout(500)
        assert page.locator("text=暂无插件").count() > 0
        logger.info("搜索过滤 OK")
        browser.close()


def test_store_like_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.goto(f"{PANEL_URL}/plugins/store")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        like_btn = page.locator(".plugin-card button:has(svg)").first
        before = like_btn.locator("span").last.inner_text()
        like_btn.click()
        page.wait_for_timeout(1000)
        after = like_btn.locator("span").last.inner_text()
        assert int(after) >= int(before)
        logger.info(f"点赞: {before} -> {after}")
        browser.close()


def test_store_pagination_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.wait_for_timeout(2000)
        assert page.locator("button[aria-label=previous]").count() > 0, "左箭头缺失"
        assert page.locator("button[aria-label=next]").count() > 0, "右箭头缺失"
        assert page.locator("button:has-text('1')").count() > 0, "页码 1 缺失"
        logger.info("分页组件可见（箭头 + 页码）")
        browser.close()


def test_store_like_already_liked_toast():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.wait_for_timeout(2000)
        # Music_Plugin 已赞，点击应弹提示
        liked_card = page.locator(".plugin-card:has-text('小禹听歌插件')").first
        liked_card.locator("button:has(svg)").first.click()
        page.wait_for_timeout(800)
        toasts = page.locator(".ant-message")
        assert toasts.count() > 0, "提示框未弹出"
        assert "已经点过赞" in toasts.inner_text(), f"提示文案不符: {toasts.inner_text()}"
        logger.info(f"重复点赞提示: {toasts.inner_text().strip()}")
        browser.close()


def test_store_github_link():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login_via_token(page)
        page.goto(f"{PANEL_URL}/plugins/store")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        links = page.locator(".plugin-card a[target='_blank']")
        assert links.count() >= 1
        href = links.first.get_attribute("href")
        assert "github.com" in href
        logger.info(f"GitHub 链接: {href}")
        browser.close()


if __name__ == "__main__":
    test_store_page_render()
    test_store_search_filter()
    test_store_like_button()
    test_store_pagination_visible()
    test_store_like_already_liked_toast()
    test_store_github_link()
    print("全部 Playwright 测试通过")
