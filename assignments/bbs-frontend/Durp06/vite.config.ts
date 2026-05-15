import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import type { UserConfigExport } from 'vite';

// Single config used by both `vite` and `vitest`. The `test` key is owned by
// vitest, not vite; we declare it via an inline cast so we don't drag in
// vitest's nested-vite types (which conflict with the top-level vite). Vitest
// reads the `test` key at runtime regardless of TS typing.
interface VitestConfig {
  environment?: string;
  globals?: boolean;
  setupFiles?: string[];
  include?: string[];
  css?: boolean;
}
type Config = UserConfigExport & { test?: VitestConfig };

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/unit/setup.ts'],
    include: ['tests/unit/**/*.test.{ts,tsx}'],
    css: false,
  },
} as Config);
