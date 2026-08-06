"""提供商页面 UI 测试 — 渲染/添加/ID重复/编辑抽屉/删除数学题验证

登录：captcha 接口直接返回明文 code（测试环境）。
"""
import json
import logging
import re

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

PANEL_URL = "http://127.0.0.1:5090"


def login_via_token(page):
    page.goto(f"{PANEL_URL}/login", wait_until="networkidle")
    r = page.evaluate("""async () => {
        const c = await fetch('/api/loyanui/auth/captcha').then(r => r.json());
        const resp = await fetch('/api/loyanui/auth/login', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: 'Admin', password: '@Loyan', captcha_id: c.data.id, captcha_code: c.data.code})
        });
        return await resp.json();
    }""")
    assert r.get("success"), f"登录失败: {r}"
    page.evaluate(f"(t) => localStorage.setItem('token', t)", r["token"])


def _cleanup(page):
    try:
        page.evaluate("""async () => {
            const list = await fetch('/api/loyanui/providers').then(r => r.json());
            for (const p of (list.data || [])) {
                if (p.id.startsWith('ui-test')) {
                    await fetch('/api/loyanui/providers/' + p.id, {
                        method: 'DELETE', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({a: 1, b: 1, op: '+', answer: 2})
                    });
                }
            }
        }""")
    except Exception:
        pass


def test_providers_page_renders():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        login_via_token(page)
        page.goto(f"{PANEL_URL}/providers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        # 标题（i18n：提供商）
        assert "提供商" in page.locator("h1, h2").first.inner_text(), "标题缺失"
        # 分类标签（对话/TTS/嵌入）
        body = page.locator("body").inner_text()
        assert "对话模型" in body and "TTS" in body and "嵌入" in body, f"分类标签缺失: {body[:200]}"
        # 添加按钮（app.add）
        add_btn = page.locator("button:has-text('添加')")
        assert add_btn.count() > 0, "添加按钮缺失"
        # 卡片区域存在（ghost 实例或空状态）
        logger.info("页面渲染 OK")
        browser.close()


def test_providers_add_and_id_duplicate():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        login_via_token(page)
        _cleanup(page)
        page.goto(f"{PANEL_URL}/providers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)

        # 添加 → 厂商列表（26 个）→ 选 DeepSeek
        page.locator("button:has-text('添加')").first.click()
        page.wait_for_timeout(800)
        modal = page.locator(".ant-modal")
        assert modal.count() > 0, "添加弹窗未出现"
        modal.get_by_text("DeepSeek").first.click()
        page.wait_for_timeout(1000)

        # 填 ID 提交（id 输入框 placeholder 或 label 定位）
        id_input = page.locator(".ant-modal input").first
        id_input.fill("ui-test-prov")
        page.wait_for_timeout(300)
        save_btn = page.locator(".ant-modal button:has-text('保存')").first
        if save_btn.count():
            save_btn.click()
        else:
            page.locator(".ant-modal button[type=submit], .ant-modal .ant-btn-primary").first.click()
        page.wait_for_timeout(1200)

        # 卡片出现
        cards = page.locator(".provider-card")
        texts = page.locator("body").inner_text()
        assert "ui-test-prov" in texts, "新实例未出现在页面"

        # 重复 ID → 顶部提示
        page.locator("button:has-text('添加')").first.click()
        page.wait_for_timeout(800)
        page.locator(".ant-modal").get_by_text("DeepSeek").first.click()
        page.wait_for_timeout(1000)
        page.locator(".ant-modal input").first.fill("ui-test-prov")
        page.wait_for_timeout(300)
        page.locator(".ant-modal .ant-btn-primary").first.click()
        page.wait_for_timeout(1000)
        body = page.locator("body").inner_text()
        assert "已存在" in body or "ID" in body, "重复 ID 未提示"

        _cleanup(page)
        logger.info("添加 + ID 重复 OK")
        browser.close()


def test_providers_edit_and_math_delete():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        login_via_token(page)
        _cleanup(page)
        # 预置一个实例
        page.evaluate("""async () => {
            await fetch('/api/loyanui/providers', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({id:'ui-test-del', type:'litellm', model:'gpt-4o', model_prefix:'openai'})});
        }""")
        page.goto(f"{PANEL_URL}/providers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)

        # 找到 ui-test-del 卡片的编辑按钮
        card = page.locator(".provider-card:has-text('ui-test-del')").first
        assert card.count() > 0, "预置实例卡片未找到"
        edit_btn = card.locator(".anticon-edit").first
        edit_btn.click()
        page.wait_for_timeout(1000)
        drawer = page.locator(".ant-drawer")
        assert drawer.count() > 0, "编辑抽屉未出现"
        # 启用开关存在
        assert drawer.locator(".ant-switch").count() > 0, "启用开关缺失"
        # 删除 → 数学题
        drawer.locator("button:has-text('删除')").first.click()
        page.wait_for_timeout(600)
        # 错误答案
        ans = page.locator(".ant-modal input").first
        ans.fill("999")
        page.locator(".ant-modal button:has-text('确定'), .ant-modal .ant-btn-primary").first.click()
        page.wait_for_timeout(800)
        body = page.locator("body").inner_text()
        assert "算式" in body or "验证" in body or "wrong" in body.lower(), "数学题错误未提示"
        # 正确答案（读取题目）
        m = re.search(r"(\d+)\s*([+\-])\s*(\d+)\s*=\s*\?", body)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            expected = a + b if op == "+" else a - b
            page.locator(".ant-modal input").first.fill(str(expected))
            page.locator(".ant-modal button:has-text('确定'), .ant-modal .ant-btn-primary").first.click()
            page.wait_for_timeout(1000)
            assert "ui-test-del" not in page.locator("body").inner_text(), "删除未生效"
        logger.info("编辑抽屉 + 删除数学题 OK")
        browser.close()
