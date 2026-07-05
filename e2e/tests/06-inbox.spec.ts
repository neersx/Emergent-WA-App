import { test, expect } from "@playwright/test";
import { ensureConnectedWaba, login } from "./_helpers";

test("inbox simulate inbound creates conversation + reply works within window", async ({
    page,
}) => {
    await login(page);
    await ensureConnectedWaba(page);
    await page.goto("/app/inbox");

    // If empty, use empty-state simulate. Otherwise, top-right simulate-new.
    const emptySimulate = page.getByTestId("inbox-empty-simulate-button");
    if (await emptySimulate.isVisible().catch(() => false)) {
        await emptySimulate.click();
    } else {
        await page.getByTestId("inbox-simulate-new-button").click();
    }

    // Wait for the conversation row
    await expect(
        page.getByTestId("inbox-conversation-row").first(),
    ).toBeVisible({ timeout: 8_000 });

    // Service window should be open
    await expect(
        page.getByTestId("window-badge-open").first(),
    ).toBeVisible();

    // Type and send a reply
    await page.fill('[data-testid="inbox-reply-input"]', "Hello from QA!");
    await page.click('[data-testid="inbox-reply-send-button"]');

    // The outbound message should appear in the thread
    await expect(
        page.locator('[data-testid="inbox-message-outbound"]').last(),
    ).toBeVisible({ timeout: 5_000 });
});
