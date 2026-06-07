// Playwright config — runs the Vite dev server automatically before tests.
// `webServer.reuseExistingServer` lets us reuse an already-running `npm run dev`
// instead of spawning a duplicate, which speeds up iteration locally.

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  // Tests share a backend — run them serially so one test's seeded user can't
  // collide with another's. We could parallelize with unique usernames per
  // test, but serial is simpler and these tests run fast.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    // Optional pause between every action so you can actually watch the
    // robot click during a --headed run. Off by default so `npm test` stays
    // fast; opt in with e.g. `SLOWMO=1500 npx playwright test --headed`.
    launchOptions: { slowMo: process.env.SLOWMO ? Number(process.env.SLOWMO) : 0 },
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  // Spin up the Vite dev server for the test run. Backend (uvicorn on :8000)
  // is the user's responsibility — the README documents starting it.
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
