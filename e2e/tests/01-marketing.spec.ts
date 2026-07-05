import { test, expect } from "@playwright/test";

test.describe("marketing", () => {
    test("home page renders with hero CTA", async ({ page }) => {
        await page.goto("/");
        await expect(page.getByTestId("hero-title")).toBeVisible();
        await expect(page.getByTestId("hero-cta-get-started")).toBeVisible();
    });

    test("pricing page shows three tiers", async ({ page }) => {
        await page.goto("/pricing");
        const tiers = page.getByTestId("pricing-tier-card");
        await expect(tiers).toHaveCount(3);
    });

    test("features page lists features", async ({ page }) => {
        await page.goto("/features");
        const cards = page.getByTestId("feature-card");
        await expect(cards.first()).toBeVisible();
    });

    test("contact form submits successfully (mock)", async ({ page }) => {
        await page.goto("/contact");
        await page.fill('[data-testid="contact-name-input"]', "QA Bot");
        await page.fill('[data-testid="contact-email-input"]', "qa@example.com");
        await page.fill(
            '[data-testid="contact-message-input"]',
            "Hello from Playwright!",
        );
        await page.click('[data-testid="contact-submit-button"]');
        await expect(
            page.getByText(/Thanks!.*business day/i),
        ).toBeVisible({ timeout: 5_000 });
    });
});
