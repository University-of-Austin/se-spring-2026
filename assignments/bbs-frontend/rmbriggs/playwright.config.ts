import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: false, // single shared SQLite DB on the backend
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    actionTimeout: 5_000,
    navigationTimeout: 10_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "python3 -m uvicorn main:app --port 8000",
      cwd: "../../bbs-webserver/rmbriggs",
      url: "http://localhost:8000/users",
      reuseExistingServer: true,
      timeout: 15_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 15_000,
      stdout: "ignore",
      stderr: "pipe",
    },
  ],
});
