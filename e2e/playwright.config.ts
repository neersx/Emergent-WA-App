import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for the WhatsApp SaaS Phase 1 MVP.
 *
 * BASE_URL: defaults to the Emergent preview URL but can be overridden.
 *   On a workstation: set BASE_URL=http://localhost:3000 (frontend) and ensure backend on :8001.
 *
 * The tests use the seeded `owner@demo.com / Owner123!` account by default.
 */
export default defineConfig({
    testDir: "./tests",
    timeout: 60_000,
    expect: { timeout: 8_000 },
    fullyParallel: false, // serial — tests share DB state (e.g. demo tenant)
    workers: 1,
    retries: process.env.CI ? 2 : 0,
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL: process.env.BASE_URL || "https://whatsapp-saas-mvp.preview.emergentagent.com",
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
        video: "retain-on-failure",
        ignoreHTTPSErrors: true,
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
        },
    ],
});
