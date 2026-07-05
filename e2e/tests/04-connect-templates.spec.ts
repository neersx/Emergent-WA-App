import { test, expect } from "@playwright/test";
import { ensureConnectedWaba, login } from "./_helpers";

test("connect WhatsApp (mock embedded signup) adds a WABA", async ({ page }) => {
    await login(page);
    await page.goto("/app/connect");
    await page.click('[data-testid="connect-launch-signup"]');
    // Recently connected list shows the new WABA
    await expect(page.getByTestId("connect-recent-list")).toBeVisible({
        timeout: 10_000,
    });
    // WABAs page lists at least one row
    await page.goto("/app/wabas");
    const rows = page.getByTestId("waba-row");
    await expect(rows.first()).toBeVisible();
});

test("templates sync from Meta in mock mode", async ({ page }) => {
    await login(page);
    await ensureConnectedWaba(page);
    await page.goto("/app/templates");
    await page.click('[data-testid="templates-sync-button"]');
    const rows = page.getByTestId("template-row");
    await expect(rows.first()).toBeVisible({ timeout: 8_000 });
    // At least 3 templates from the mock set
    expect(await rows.count()).toBeGreaterThanOrEqual(3);
});
