/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // E2E specs in tests/ use @playwright/test and are run by
    // `npm run test:e2e`, not by Vitest.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
})
