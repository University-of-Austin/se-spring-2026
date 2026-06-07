// Tests for the apiFetch chokepoint.  These are real tests of real
// behavior: they exercise the parsing of A2's actual error envelope
// shape and the network-failure normalization that the whole UI
// depends on.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ApiError, apiFetch } from "./client";

describe("apiFetch", () => {
  const realFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  it("parses A2's single-string {detail} envelope on a 422", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "message must be between 1 and 500 characters" }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    let caught: unknown;
    try {
      await apiFetch("/posts");
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(422);
    expect((caught as ApiError).detail).toBe(
      "message must be between 1 and 500 characters",
    );
  });

  it("converts a network failure into ApiError with status 0", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new TypeError("Failed to fetch"),
    );

    let caught: unknown;
    try {
      await apiFetch("/posts");
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(0);
    expect((caught as ApiError).detail).toMatch(/cannot reach/i);
  });

  it("returns undefined for a 204 (DELETE /posts/{id})", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );

    const result = await apiFetch("/posts/42", { method: "DELETE" });
    expect(result).toBeUndefined();
  });
});
