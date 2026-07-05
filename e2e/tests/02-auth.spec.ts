import { test, expect } from "@playwright/test";
import { login, register, uniqueEmail } from "./_helpers";

test.describe("auth", () => {
    test("register creates tenant and lands on dashboard", async ({ page }) => {
        const email = uniqueEmail("reg");
        await register(page, email, "Password123!", "PW Tenant");
        await expect(page.getByTestId("admin-tenant-name")).toContainText(
            "PW Tenant",
        );
    });

    test("login with seeded demo owner lands on dashboard without MFA", async ({
        page,
    }) => {
        await login(page);
        await expect(page.getByTestId("admin-page-title")).toContainText(
            /Dashboard/i,
        );
        // Mock badge is visible
        await expect(page.getByTestId("admin-mock-badge")).toBeVisible();
    });

    test("login with wrong password shows error", async ({ page }) => {
        await page.goto("/login");
        await page.fill('[data-testid="login-email-input"]', "owner@demo.com");
        await page.fill(
            '[data-testid="login-password-input"]',
            "this-is-wrong",
        );
        await page.click('[data-testid="login-submit-button"]');
        await expect(page.getByText(/Invalid credentials/i)).toBeVisible({
            timeout: 5_000,
        });
    });
});
