// Extends Vitest's `expect` with jest-dom matchers like `.toBeInTheDocument()`.
// Auto-cleans up React Testing Library renders between tests.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
