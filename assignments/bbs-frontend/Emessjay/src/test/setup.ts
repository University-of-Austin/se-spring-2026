// Vitest global setup.  Pulls in jest-dom's matchers (toBeInTheDocument,
// toHaveTextContent, …) so tests read naturally.

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
