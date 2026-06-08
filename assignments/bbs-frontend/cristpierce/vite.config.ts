/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
//
// The backend base URL is read at runtime from import.meta.env.VITE_API_BASE
// (see src/lib/api.ts), so there is intentionally no dev proxy here — the
// browser talks to the A2 API directly and the server opts in via CORS.
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    css: true,
    include: ['tests/**/*.test.{ts,tsx}'],
    // Playwright specs live in tests/e2e and are run by Playwright, not Vitest.
    exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**'],
      exclude: ['src/main.tsx', 'src/vite-env.d.ts'],
    },
  },
})
