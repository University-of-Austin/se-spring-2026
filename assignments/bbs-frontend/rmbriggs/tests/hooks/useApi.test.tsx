import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useApi } from "@/hooks/useApi";

describe("useApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("test_useApi_starts_in_loading_state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useApi<string[]>("/users"));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("test_useApi_transitions_to_success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(["alice"]), { status: 200, headers: { "content-type": "application/json" } }),
    );
    const { result } = renderHook(() => useApi<string[]>("/users"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["alice"]);
    expect(result.current.error).toBeNull();
  });

  it("test_useApi_transitions_to_error_on_500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "boom" }), { status: 500, headers: { "content-type": "application/json" } }),
    );
    const { result } = renderHook(() => useApi<string[]>("/users"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatchObject({ status: 500 });
  });
});
