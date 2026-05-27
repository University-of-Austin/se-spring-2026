import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCurrentUser } from "../src/hooks/useCurrentUser";

describe("useCurrentUser", () => {
  it("starts null when localStorage is empty, persists on set, and clears", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.username).toBeNull();

    act(() => {
      result.current.setUsername("alice");
    });
    expect(result.current.username).toBe("alice");
    expect(localStorage.getItem("bbs.username")).toBe("alice");

    act(() => {
      result.current.clear();
    });
    expect(result.current.username).toBeNull();
    expect(localStorage.getItem("bbs.username")).toBeNull();
  });

  it("reads an existing localStorage value on mount", () => {
    localStorage.setItem("bbs.username", "bob");
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.username).toBe("bob");
  });

  it("syncs across tabs via the storage event", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.username).toBeNull();

    act(() => {
      const ev = new StorageEvent("storage", {
        key: "bbs.username",
        newValue: "carol",
      });
      window.dispatchEvent(ev);
    });
    expect(result.current.username).toBe("carol");
  });
});
