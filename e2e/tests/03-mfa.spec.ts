import { test, expect } from "@playwright/test";
import { authenticator } from "otplib";
import { register, uniqueEmail } from "./_helpers";

test("MFA enrollment + verify", async ({ page }) => {
    const email = uniqueEmail("mfa");
    await register(page, email, "Password123!", "MFA Tenant");
    await page.goto("/app/security");
    await page.click('[data-testid="mfa-setup-start"]');
    const secret = await page
        .getByTestId("mfa-secret")
        .innerText();
    expect(secret.length).toBeGreaterThan(10);

    const code = authenticator.generate(secret.replace(/\s+/g, ""));
    await page.locator('[data-testid="mfa-otp-input"] input').first().fill(code);
    // Fallback: paste into individual slots if needed
    await page.click('[data-testid="mfa-verify-button"]');

    await expect(page.getByTestId("mfa-status-on")).toBeVisible({
        timeout: 8_000,
    });
});
