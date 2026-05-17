import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "../src/api/client";
import { ApiError } from "../src/api/types";

describe("apiFetch", () => {
  const realFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  function mockResponse(opts: {
    ok?: boolean;
    status?: number;
    statusText?: string;
    body?: unknown;
  }): Response {
    const status = opts.status ?? 200;
    const text = opts.body === undefined ? "" : JSON.stringify(opts.body);
    return {
      ok: opts.ok ?? status < 400,
      status,
      statusText: opts.statusText ?? "",
      text: () => Promise.resolve(text),
    } as Response;
  }

  it("returns parsed JSON for 2xx responses", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ body: { hello: "world" } }),
    );
    const result = await apiFetch<{ hello: string }>("/anything");
    expect(result).toEqual({ hello: "world" });
  });

  it("returns undefined for 204 No Content", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ status: 204 }),
    );
    const result = await apiFetch<void>("/anything", { method: "DELETE" });
    expect(result).toBeUndefined();
  });

  it("flattens FastAPI 422 validation errors into a useful detail", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({
        status: 422,
        ok: false,
        body: {
          detail: [
            { loc: ["body", "message"], msg: "field required", type: "x" },
            { loc: ["body", "message"], msg: "ensure length >= 1", type: "y" },
          ],
        },
      }),
    );
    await expect(apiFetch("/anything")).rejects.toMatchObject({
      status: 422,
      detail: "field required; ensure length >= 1",
    });
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError);
  });

  it("passes through string `detail` for plain HTTPException responses", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({
        status: 404,
        ok: false,
        body: { detail: "user not found" },
      }),
    );
    await expect(apiFetch("/anything")).rejects.toMatchObject({
      status: 404,
      detail: "user not found",
    });
  });

  it("wraps network failures as an ApiError with status 0", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new TypeError("Failed to fetch"),
    );
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/anything")).rejects.toMatchObject({ status: 0 });
  });
});
