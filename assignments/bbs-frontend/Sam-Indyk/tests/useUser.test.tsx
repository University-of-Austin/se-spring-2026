import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useUser } from "../src/hooks/useUser";

describe("useUser", () => {
  it("starts with null when nothing is stored", () => {
    const { result } = renderHook(() => useUser());
    expect(result.current.username).toBeNull();
  });

  it("persists the username to localStorage", () => {
    const { result } = renderHook(() => useUser());
    act(() => result.current.setUsername("alice"));
    expect(result.current.username).toBe("alice");
    expect(localStorage.getItem("bbs.username")).toBe("alice");
  });

  it("signOut clears the username everywhere", () => {
    localStorage.setItem("bbs.username", "alice");
    const { result } = renderHook(() => useUser());
    expect(result.current.username).toBe("alice");
    act(() => result.current.signOut());
    expect(result.current.username).toBeNull();
    expect(localStorage.getItem("bbs.username")).toBeNull();
  });

  it("hooks in different components stay in sync via the custom event", () => {
    const a = renderHook(() => useUser());
    const b = renderHook(() => useUser());
    act(() => a.result.current.setUsername("bob"));
    // Both should observe the same value.
    expect(a.result.current.username).toBe("bob");
    expect(b.result.current.username).toBe("bob");
  });
});
