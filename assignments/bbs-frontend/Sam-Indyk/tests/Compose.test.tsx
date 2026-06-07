import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Compose } from "../src/components/Compose";

const originalFetch = globalThis.fetch;

function makeResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup() {
  const onOptimistic = vi.fn();
  const onSettled = vi.fn();
  render(
    <MemoryRouter>
      <Compose onOptimistic={onOptimistic} onSettled={onSettled} />
    </MemoryRouter>
  );
  return { onOptimistic, onSettled };
}

describe("<Compose />", () => {
  beforeEach(() => {
    localStorage.setItem("bbs.username", "alice");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows a sign-in prompt when no user is set", () => {
    localStorage.removeItem("bbs.username");
    render(
      <MemoryRouter>
        <Compose onOptimistic={() => {}} onSettled={() => {}} />
      </MemoryRouter>
    );
    expect(screen.getByText(/need to be signed in/i)).toBeInTheDocument();
  });

  it("disables the post button when input is empty", () => {
    setup();
    const btn = screen.getByRole("button", { name: /post/i });
    expect(btn).toBeDisabled();
  });

  it("shows a character count that turns 'over' past the limit", async () => {
    setup();
    const textarea = screen.getByLabelText(/new post as/i);
    // fireEvent.change to set the value in one shot — typing 501 chars one
    // keystroke at a time times out and leaks across tests.
    fireEvent.change(textarea, { target: { value: "x".repeat(501) } });
    const count = await screen.findByText(/^501\/500$/);
    expect(count).toHaveClass("over");
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("submits optimistically, then reconciles on server success", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      makeResponse(
        {
          id: 99,
          username: "alice",
          message: "hello world",
          created_at: "2026-05-13T00:00:00",
          updated_at: null,
          reactions: {},
        },
        201
      )
    );
    globalThis.fetch = fetchMock;

    const { onOptimistic, onSettled } = setup();
    const user = userEvent.setup({ delay: null });
    const textarea = screen.getByLabelText(/new post as/i);

    fireEvent.change(textarea, { target: { value: "hello world" } });
    await user.click(screen.getByRole("button", { name: /post/i }));

    // Optimistic call fires synchronously with the submit.
    await waitFor(() => expect(onOptimistic).toHaveBeenCalledOnce());
    const pending = onOptimistic.mock.calls[0][0];
    expect(pending.message).toBe("hello world");
    expect(pending.id).toBeLessThan(0); // synthetic negative id

    await waitFor(() => expect(onSettled).toHaveBeenCalledOnce());
    const settled = onSettled.mock.calls[0][0];
    expect(settled.ok).toBe(true);
    if (settled.ok) {
      expect(settled.post.id).toBe(99);
      expect(settled.pendingId).toBe(pending.id);
    }

    // Field clears on success.
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("rolls back: surfaces server 422 detail and restores the text", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      makeResponse({ detail: "message too short" }, 422)
    );
    globalThis.fetch = fetchMock;

    const { onOptimistic, onSettled } = setup();
    const user = userEvent.setup({ delay: null });
    const textarea = screen.getByLabelText(/new post as/i);

    fireEvent.change(textarea, { target: { value: "boom" } });
    await user.click(screen.getByRole("button", { name: /post/i }));

    await waitFor(() => expect(onOptimistic).toHaveBeenCalledOnce());
    await waitFor(() => expect(onSettled).toHaveBeenCalledOnce());

    const settled = onSettled.mock.calls[0][0];
    expect(settled.ok).toBe(false);

    // Server error appears inline.
    expect(await screen.findByText(/message too short/i)).toBeInTheDocument();
    // Text is restored so the user doesn't lose their work.
    expect((textarea as HTMLTextAreaElement).value).toBe("boom");
  });
});
