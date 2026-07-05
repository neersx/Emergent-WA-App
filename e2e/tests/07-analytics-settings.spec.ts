import { test, expect } from "@playwright/test";
import { ensureConnectedWaba, login } from "./_helpers";

test("analytics page renders charts with data", async ({ page }) => {
    await login(page);
    await ensureConnectedWaba(page);
    await page.goto("/app/analytics");
    await expect(page.getByTestId("analytics-stat-total")).toBeVisible();
    // Timeseries chart container exists
    await expect(page.getByTestId("analytics-timeseries-chart")).toBeVisible();
});

test("settings page reflects MOCK MODE", async ({ page }) => {
    await login(page);
    await page.goto("/app/settings");
    await expect(page.getByText(/Platform Settings/i)).toBeVisible();
    await expect(page.getByText(/MOCK MODE/i).first()).toBeVisible();
});
