import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the A4 end-to-end spec.
 *
 * Two-server orchestration:
 *   - The frontend (Vite dev) is auto-started via webServer below.
 *   - The A2 backend must be running separately on :8000. Start it
 *     with `cd assignments/bbs-webserver/kylehchoy && uvicorn main:app
 *     --port 8000` (see top-level README §1). Playwright doesn't
 *     manage A2 because A2 is a Python process owned by a separate
 *     assignment dir; mixing the two would bake a Python toolchain
 *     into this package's test-time deps, which is the wrong
 *     dependency direction.
 *   - On CI both would be in the workflow's `services:` block.
 *
 * Spec lives at tests/e2e/full-flow.spec.ts. Unit tests in
 * tests/components/ are excluded via testMatch so vitest and
 * playwright don't trip over each other.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
