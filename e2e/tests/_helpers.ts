/** Shared helpers for E2E tests. */
import { Page, expect } from "@playwright/test";

export const DEMO_EMAIL = "owner@demo.com";
export const DEMO_PASSWORD = "Owner123!";

export async function login(
    page: Page,
    email: string = DEMO_EMAIL,
    password: string = DEMO_PASSWORD,
): Promise<void> {
    await page.goto("/login");
    await page.fill('[data-testid="login-email-input"]', email);
    await page.fill('[data-testid="login-password-input"]', password);
    await page.click('[data-testid="login-submit-button"]');
    await page.waitForURL(/\/app\/dashboard/);
}

export async function register(
    page: Page,
    email: string,
    password: string,
    tenantName: string,
): Promise<void> {
    await page.goto("/register");
    await page.fill('[data-testid="register-tenant-name-input"]', tenantName);
    await page.fill('[data-testid="register-email-input"]', email);
    await page.fill('[data-testid="register-password-input"]', password);
    await page.click('[data-testid="register-submit-button"]');
    await page.waitForURL(/\/app\/dashboard/);
}

/** Connect a WABA via the (mock) Embedded Signup flow. */
export async function ensureConnectedWaba(page: Page): Promise<void> {
    await page.goto("/app/wabas");
    const empty = page.getByTestId("empty-state");
    if (await empty.isVisible().catch(() => false)) {
        await page.goto("/app/connect");
        await page.click('[data-testid="connect-launch-signup"]');
        // Wait for the success toast / list to populate
        await expect(
            page.getByText(/Connected WABA/i).first(),
        ).toBeVisible({ timeout: 10_000 });
    }
}

export function uniqueEmail(prefix: string = "qa"): string {
    return `${prefix}+${Date.now()}@example.com`;
}
