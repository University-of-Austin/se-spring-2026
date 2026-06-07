import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the BBS frontend e2e suite.
 *
 * Spins up the Vite dev server on :5173 automatically. Expects the A2
 * backend to be running on :8000 separately (see README §How to run).
 * Trying to manage uvicorn from here too would pull in Python/venv
 * setup that's better kept out of the JS toolchain.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    actionTimeout: 5000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
