import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Compose } from "../src/components/Compose";
import { AuthProvider } from "../src/auth";

// Mock the api module so Compose's submit doesn't hit a real server.
vi.mock("../src/api", () => ({
  api: {
    listBoards: vi.fn(async () => [
      { name: "general", created_at: "2026-05-01T00:00:00", post_count: 12 },
      { name: "random",  created_at: "2026-05-02T00:00:00", post_count: 3 },
    ]),
    createPost: vi.fn(async (msg: string) => ({
      id: 999,
      username: "alice",
      board: "general",
      message: msg,
      created_at: "2026-05-15T12:00:00",
      updated_at: null,
    })),
  },
}));

function renderWithAuth(ui: React.ReactNode, withSession = true) {
  if (withSession) {
    localStorage.setItem("bbs.username", "alice");
    localStorage.setItem("bbs.token", "tok-123");
  }
  return render(
    <MemoryRouter>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>,
  );
}

describe("Compose", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("disables the post button when the textarea is empty", () => {
    const noop = vi.fn();
    renderWithAuth(
      <Compose onOptimisticAdd={noop} onConfirm={noop} onRollback={noop} />,
    );
    const btn = screen.getByRole("button", { name: /post message/i });
    expect(btn).toBeDisabled();
  });

  it("enables the post button once the user types non-whitespace", () => {
    const noop = vi.fn();
    renderWithAuth(
      <Compose onOptimisticAdd={noop} onConfirm={noop} onRollback={noop} />,
    );
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "hello!" } });
    const btn = screen.getByRole("button", { name: /post message/i });
    expect(btn).not.toBeDisabled();
  });

  it("turns the character counter red once over 500 chars and disables submit", () => {
    const noop = vi.fn();
    renderWithAuth(
      <Compose onOptimisticAdd={noop} onConfirm={noop} onRollback={noop} />,
    );
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "x".repeat(501) } });

    const counter = screen.getByText("501 / 500");
    expect(counter).toHaveClass("char-count-over");

    const btn = screen.getByRole("button", { name: /post message/i });
    expect(btn).toBeDisabled();
  });

  it("invokes onOptimisticAdd then onConfirm on a successful post", async () => {
    const onOptimisticAdd = vi.fn();
    const onConfirm = vi.fn();
    const onRollback = vi.fn();

    renderWithAuth(
      <Compose
        onOptimisticAdd={onOptimisticAdd}
        onConfirm={onConfirm}
        onRollback={onRollback}
      />,
    );
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "hi there" } });

    const btn = screen.getByRole("button", { name: /post message/i });
    fireEvent.click(btn);

    // Optimistic placeholder added synchronously
    expect(onOptimisticAdd).toHaveBeenCalledTimes(1);
    const placeholder = onOptimisticAdd.mock.calls[0][0];
    expect(placeholder.message).toBe("hi there");
    expect(placeholder.id).toBeLessThan(0);

    // Confirmation happens after the mocked api resolves -- wait for the
    // message textarea to clear (not the board input, which is also empty).
    await waitFor(() => {
      const ta = screen.getByLabelText("Message") as HTMLTextAreaElement;
      expect(ta.value).toBe("");
    });
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onRollback).not.toHaveBeenCalled();
  });

  it("shows a sign-in prompt when there's no logged-in user", () => {
    const noop = vi.fn();
    renderWithAuth(
      <Compose onOptimisticAdd={noop} onConfirm={noop} onRollback={noop} />,
      false,
    );
    expect(screen.getByText(/not signed in/i)).toBeInTheDocument();
  });
});
