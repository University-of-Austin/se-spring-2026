import { defineConfig, devices } from '@playwright/test';

// E2E config. Playwright auto-starts the Vite dev server via webServer; the
// A2 backend must be running separately on http://localhost:8000 (see README
// — the spec's two-terminal model).
export default defineConfig({
  testDir: './tests/e2e',
  // Tests mutate the real backend DB, so serial runs avoid races.
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  retries: 0,
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
