// Playwright config for the user-flow E2E test.
//
// The webServer array starts BOTH the A2 backend and the Vite dev
// server before tests run — so the entire end-to-end stack is
// brought up by a single `npm run test:e2e` invocation, as the gold
// tier requires.
//
// reuseExistingServer is true in dev so that when you already have
// uvicorn / vite running in their own terminals, the tests just
// hook into them rather than fighting over the ports.

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  webServer: [
    {
      // Start the A2 FastAPI server using the venv's uvicorn so we
      // don't depend on whatever uvicorn the user has globally.
      command: "../.venv/bin/uvicorn main:app --port 8000",
      cwd: "../../bbs-webserver/Emessjay/webserver",
      url: "http://localhost:8000/users",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
