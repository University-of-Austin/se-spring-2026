import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { UserProvider, useCurrentUser } from "@/hooks/useCurrentUser";

const wrapper = ({ children }: { children: React.ReactNode }) => <UserProvider>{children}</UserProvider>;

describe("useCurrentUser", () => {
  beforeEach(() => localStorage.clear());

  it("test_useCurrentUser_returns_null_when_localStorage_empty", () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBeNull();
  });

  it("test_useCurrentUser_returns_stored_username_on_mount", () => {
    localStorage.setItem("username", "alice");
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBe("alice");
  });

  it("test_setUsername_persists_to_localStorage", () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    act(() => result.current.setUsername("bob"));
    expect(localStorage.getItem("username")).toBe("bob");
    expect(result.current.username).toBe("bob");
  });

  it("test_clearUsername_removes_from_localStorage", () => {
    localStorage.setItem("username", "alice");
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    act(() => result.current.clearUsername());
    expect(localStorage.getItem("username")).toBeNull();
    expect(result.current.username).toBeNull();
  });
});
