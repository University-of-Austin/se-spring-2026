import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiFetch } from "@/api/client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("test_apiFetch_includes_X_Username_when_set", async () => {
    localStorage.setItem("username", "alice");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }),
    );

    await apiFetch("/users");

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Username"]).toBe("alice");
  });

  it("test_apiFetch_omits_X_Username_when_unset", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", { status: 200, headers: { "content-type": "application/json" } }),
    );

    await apiFetch("/users");

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Username"]).toBeUndefined();
  });

  it("test_apiFetch_throws_ApiError_on_4xx_with_detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "User not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiFetch("/users/nope")).rejects.toMatchObject({ status: 404, detail: "User not found" });
  });

  it("test_apiFetch_returns_parsed_json_on_2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ username: "alice" }]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const result = await apiFetch("/users");

    expect(result).toEqual([{ username: "alice" }]);
  });

  it("test_apiFetch_handles_204_with_no_body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));

    const result = await apiFetch("/posts/1", { method: "DELETE" });

    expect(result).toBeNull();
  });
});
