import { describe, it, expect, beforeEach, vi } from "vitest";
import { request, ApiError } from "../src/api/client";

describe("api client", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("returns parsed JSON on 200", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const data = await request<{ ok: boolean }>("/x");
    expect(data.ok).toBe(true);
  });

  it("throws ApiError with detail string on 4xx", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "user not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );
    let caught: unknown;
    try {
      await request("/users/ghost");
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(404);
    expect((caught as ApiError).message).toBe("user not found");
  });

  it("extracts msg from 422 validation arrays", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ loc: ["body", "message"], msg: "String too short", type: "x" }],
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );
    await expect(request("/posts", { method: "POST", body: { message: "" } })).rejects.toMatchObject(
      { status: 422, message: "String too short" },
    );
  });

  it("sends X-Username header when username is provided", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    await request("/posts/9", { method: "DELETE", username: "alice" });
    const init = spy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Username"]).toBe("alice");
  });

  it("returns undefined for 204 responses", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const result = await request("/posts/1", { method: "DELETE", username: "alice" });
    expect(result).toBeUndefined();
  });
});
