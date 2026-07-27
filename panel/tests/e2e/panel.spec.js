import { test, expect } from "@playwright/test";

test.describe("LoyanBot Panel", () => {
  test("login page loads correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.locator("input[id*='username'], input[id*='password']").first()).toBeVisible();
  });

  test("all protected routes redirect to /login", async ({ page }) => {
    const routes = [
      "/", "/adapters", "/adapters/create", "/providers",
      "/providers/create", "/ai-tools", "/ai-tools/mcp",
      "/ai-tools/knowledge", "/ai-tools/memory", "/ai-tools/agent",
      "/ai-tools/skill", "/plugins/market", "/plugins/manage",
      "/plugins/toolbox", "/logs", "/settings", "/settings/ai",
      "/settings/general",
    ];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForURL(/\/login/);
      expect(page.url()).toContain("/login");
    }
  });

  test("language switcher is visible on login page", async ({ page }) => {
    await page.goto("/login");
    const langSelect = page.locator(".ant-select");
    await expect(langSelect.first()).toBeVisible();
  });

  test("no JS errors on login page", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.goto("/login");
    await page.waitForTimeout(2000);
    expect(errors.length).toBe(0);
  });

  test("404 unknown routes redirect to login", async ({ page }) => {
    await page.goto("/unknown-route-test");
    await page.waitForURL(/\/login/);
    expect(page.url()).toContain("/login");
  });
});
