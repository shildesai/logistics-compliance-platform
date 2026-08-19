import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Set PLAYWRIGHT_CHROMIUM_PATH to reuse a pre-installed browser
        // (e.g. in a sandboxed CI image) instead of Playwright's own
        // download. Leave unset for a normal `npx playwright install` setup.
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
          : undefined,
      },
    },
  ],
  // The dev server is started separately (see README.md / package.json
  // "test:e2e" script) so the API is guaranteed to be up first too.
});
