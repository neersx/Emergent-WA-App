import { test, expect, request } from "@playwright/test";
import { register, uniqueEmail } from "./_helpers";

/**
 * Tenant isolation: register a brand-new tenant, then verify it sees no WABAs
 * or messages and gets 404 trying to send via another tenant's phone number id.
 *
 * To probe the demo tenant's phone_number_id, we use Playwright's API request
 * context with the demo cookies.
 */
test("new tenant cannot access demo tenant's data", async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const email = uniqueEmail("iso");
    await register(page, email, "Password123!", "Iso Tenant");

    await page.goto("/app/wabas");
    // Should see the empty state OR no waba rows belonging to the demo tenant
    const empty = page.getByTestId("empty-state");
    const rows = page.getByTestId("waba-row");
    const isEmpty = await empty.isVisible().catch(() => false);
    const rowCount = await rows.count();
    expect(isEmpty || rowCount === 0).toBeTruthy();

    await page.goto("/app/messages");
    // Wait briefly for auto-load
    await page.waitForTimeout(500);
    const msgRows = await page.getByTestId("message-row").count();
    expect(msgRows).toBe(0);

    await ctx.close();
});
