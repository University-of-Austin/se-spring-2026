import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "../src/auth";

vi.mock("../src/api", () => ({
  api: {
    login: vi.fn(async (username: string) => ({ username, token: "fake-token-xyz" })),
    signup: vi.fn(async (username: string) => ({
      username, created_at: "2026-05-15T00:00:00", bio: null, post_count: 0,
    })),
    logout: vi.fn(async () => undefined),
  },
}));

function Harness() {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="username">{auth.username ?? "(none)"}</div>
      <div data-testid="token">{auth.token ?? "(none)"}</div>
      <button onClick={() => auth.login("alice", "pw")}>do-login</button>
      <button onClick={() => auth.logout()}>do-logout</button>
    </div>
  );
}

describe("AuthProvider + useAuth", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts unauthenticated with no localStorage values", () => {
    render(<AuthProvider><Harness /></AuthProvider>);
    expect(screen.getByTestId("username")).toHaveTextContent("(none)");
    expect(screen.getByTestId("token")).toHaveTextContent("(none)");
  });

  it("hydrates identity from localStorage on mount", () => {
    localStorage.setItem("bbs.username", "alice");
    localStorage.setItem("bbs.token", "stored-token");
    render(<AuthProvider><Harness /></AuthProvider>);
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
    expect(screen.getByTestId("token")).toHaveTextContent("stored-token");
  });

  it("login() updates state and persists to localStorage", async () => {
    render(<AuthProvider><Harness /></AuthProvider>);
    fireEvent.click(screen.getByText("do-login"));
    await waitFor(() => {
      expect(screen.getByTestId("username")).toHaveTextContent("alice");
    });
    expect(localStorage.getItem("bbs.username")).toBe("alice");
    expect(localStorage.getItem("bbs.token")).toBe("fake-token-xyz");
  });

  it("logout() clears state and removes localStorage", async () => {
    localStorage.setItem("bbs.username", "alice");
    localStorage.setItem("bbs.token", "stored");
    render(<AuthProvider><Harness /></AuthProvider>);
    fireEvent.click(screen.getByText("do-logout"));
    await waitFor(() => {
      expect(screen.getByTestId("username")).toHaveTextContent("(none)");
    });
    expect(localStorage.getItem("bbs.username")).toBeNull();
    expect(localStorage.getItem("bbs.token")).toBeNull();
  });
});
