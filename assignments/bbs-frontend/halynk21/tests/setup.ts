import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach } from 'vitest';
import { cleanup } from '@testing-library/react';

beforeEach(() => {
  // Each test starts with a clean localStorage so state doesn't leak.
  localStorage.clear();
});

afterEach(() => {
  cleanup();
});
