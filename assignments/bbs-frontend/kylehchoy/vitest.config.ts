import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: false,
    include: ['tests/components/**/*.test.{ts,tsx}'],
    // Playwright specs live in tests/e2e and are run via `npm run test:e2e`.
    exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
  },
})
