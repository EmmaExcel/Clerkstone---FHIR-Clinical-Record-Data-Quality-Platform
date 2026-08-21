import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run against a locally-built Clerkstone stack:
 *   1. `npm run build && npm run start` (the Next.js web app)
 *   2. the FastAPI backend (see repo README / Makefile `make dev`)
 *
 * Accessibility scans use @axe-core/playwright against every page.
 * Browsers must be installed once with `npx playwright install`.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
