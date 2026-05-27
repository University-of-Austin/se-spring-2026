import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../src/auth/AuthContext";

function Probe() {
  const { username, setUsername, signOut } = useAuth();
  return (
    <div>
      <span data-testid="who">{username ?? "(none)"}</span>
      <button onClick={() => setUsername("alice")}>set alice</button>
      <button onClick={signOut}>sign out</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => localStorage.clear());

  it("starts empty when no username is in localStorage", () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("who").textContent).toBe("(none)");
  });

  it("hydrates from localStorage on mount", () => {
    localStorage.setItem("bbs.username", "bob");
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("who").textContent).toBe("bob");
  });

  it("persists set/sign-out to localStorage", () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    act(() => {
      screen.getByText("set alice").click();
    });
    expect(localStorage.getItem("bbs.username")).toBe("alice");
    act(() => {
      screen.getByText("sign out").click();
    });
    expect(localStorage.getItem("bbs.username")).toBeNull();
  });
});
