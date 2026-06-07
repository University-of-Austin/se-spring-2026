// Playwright config for the user-flow E2E test.
//
// The webServer array starts BOTH the A2 backend and the Vite dev
// server before tests run — so the entire end-to-end stack is
// brought up by a single `npm run test:e2e` invocation, as the gold
// tier requires.
//
// The e2e stack runs on its own port pair (backend 8001, frontend
// 5174) and its own SQLite file (bbs-e2e.db).  This isolates it
// from any dev uvicorn/vite running on 8000/5173 against the real
// bbs.db, so the test cannot pollute the production database.
// reuseExistingServer is left false for both so we never latch
// onto a stray server pointed at the wrong DB.

import { defineConfig, devices } from "@playwright/test";

const E2E_API_PORT = 8001;
const E2E_WEB_PORT = 5174;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: `http://localhost:${E2E_WEB_PORT}`,
    trace: "on-first-retry",
  },
  webServer: [
    {
      // Start the A2 FastAPI server using the venv's uvicorn so we
      // don't depend on whatever uvicorn the user has globally.
      // BBS_DB_FILE points at a dedicated e2e SQLite file so the
      // real bbs.db is never touched.
      command: `../.venv/bin/uvicorn main:app --port ${E2E_API_PORT}`,
      cwd: "../../bbs-webserver/Emessjay/webserver",
      env: { BBS_DB_FILE: "bbs-e2e.db" },
      url: `http://localhost:${E2E_API_PORT}/users`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Vite picks up VITE_API_BASE at startup; the frontend's
      // api/client.ts reads it via import.meta.env.  Forcing the
      // port here keeps the e2e frontend on its own slot so it
      // doesn't collide with a dev `npm run dev` on 5173.
      command: `npm run dev -- --port ${E2E_WEB_PORT} --strictPort`,
      env: { VITE_API_BASE: `http://localhost:${E2E_API_PORT}` },
      url: `http://localhost:${E2E_WEB_PORT}`,
      reuseExistingServer: false,
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
