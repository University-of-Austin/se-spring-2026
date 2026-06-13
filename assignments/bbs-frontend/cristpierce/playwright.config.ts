import { defineConfig, devices } from '@playwright/test'

// The e2e suite is hermetic: it serves the real frontend via `npm run dev` and
// intercepts the API at the network layer (see tests/e2e/flow.spec.ts), so it
// runs with one command and needs no backend / Python / database. The dedicated
// port avoids clashing with a dev server you may already have on 5173.
const PORT = 5179
const BASE_URL = `http://localhost:${PORT}`

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
