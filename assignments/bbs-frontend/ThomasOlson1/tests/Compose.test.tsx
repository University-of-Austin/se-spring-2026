import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider } from "../src/auth/AuthContext";
import { ToastProvider } from "../src/components/Toast";
import { Compose } from "../src/components/Compose";

function renderWithProviders(ui: React.ReactElement, { username = "alice" } = {}) {
  if (username) localStorage.setItem("bbs.username", username);
  return render(
    <AuthProvider>
      <ToastProvider>{ui}</ToastProvider>
    </AuthProvider>,
  );
}

describe("Compose", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("disables the post button when the textarea is empty", () => {
    renderWithProviders(<Compose />);
    const btn = screen.getByRole("button", { name: /post/i });
    expect(btn).toBeDisabled();
  });

  it("turns the character counter red past 500 chars", async () => {
    renderWithProviders(<Compose />);
    const ta = screen.getByLabelText(/new post/i);
    await userEvent.type(ta, "x".repeat(20), { delay: 0 });
    const counter = screen.getByText(/\/500$/);
    expect(counter.className).not.toMatch(/over/);

    const longText = "y".repeat(501);
    // Use fireEvent-style direct value set to avoid 501-keystroke loop
    (ta as HTMLTextAreaElement).value = longText;
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    // The bare DOM event doesn't trigger React's synthetic event; type one more char so React reads value
    await userEvent.type(ta, "z", { delay: 0 });
    expect(screen.getByText(/^\d+\/500$/).className).toMatch(/over/);
  });

  it("locks the form and shows a sign-in prompt when no user is set", () => {
    renderWithProviders(<Compose />, { username: "" });
    expect(screen.queryByLabelText(/new post/i)).not.toBeInTheDocument();
    expect(screen.getByText(/sign in or create a user/i)).toBeInTheDocument();
  });

  it("submits via the API client when the post button is clicked", async () => {
    const mockFetch = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1,
          username: "alice",
          message: "hello",
          created_at: "2026-01-01T00:00:00",
          updated_at: null,
          board: "general",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    const onCreated = vi.fn();
    renderWithProviders(<Compose onCreated={onCreated} />);
    await userEvent.type(screen.getByLabelText(/new post/i), "hello");
    await userEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(String(url)).toMatch(/\/posts$/);
    expect((init as RequestInit).method).toBe("POST");
    expect(((init as RequestInit).headers as Record<string, string>)["X-Username"]).toBe(
      "alice",
    );
  });
});
