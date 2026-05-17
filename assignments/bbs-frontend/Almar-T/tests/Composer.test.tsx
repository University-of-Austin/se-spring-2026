import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Composer } from "../src/components/Composer";

function renderComposer(props: {
  currentUser: string | null;
  onSubmit?: (msg: string) => Promise<void>;
}) {
  return render(
    <MemoryRouter>
      <Composer
        currentUser={props.currentUser}
        onSubmit={props.onSubmit ?? (() => Promise.resolve())}
      />
    </MemoryRouter>,
  );
}

describe("Composer", () => {
  it("hides the form when no user is signed in", () => {
    renderComposer({ currentUser: null });
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });

  it("disables the post button when input is empty or only whitespace", async () => {
    const user = userEvent.setup();
    renderComposer({ currentUser: "alice" });
    const button = screen.getByRole("button", { name: /post message/i });
    expect(button).toBeDisabled();
    await user.type(screen.getByRole("textbox"), "   ");
    expect(button).toBeDisabled();
    await user.type(screen.getByRole("textbox"), "hello");
    expect(button).toBeEnabled();
  });

  it("turns char count red past 500 chars and blocks submit", async () => {
    const user = userEvent.setup();
    renderComposer({ currentUser: "alice" });
    const textarea = screen.getByRole("textbox");
    const long = "a".repeat(501);
    // Paste rather than typing each char — much faster for big strings.
    await user.click(textarea);
    await user.paste(long);
    const count = screen.getByText(/501\/500/);
    expect(count).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /post message/i });
    expect(button).toBeDisabled();
  });

  it("calls onSubmit with trimmed text and clears the textarea on success", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderComposer({ currentUser: "alice", onSubmit });
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "  hello world  ");
    await user.click(screen.getByRole("button", { name: /post message/i }));
    expect(onSubmit).toHaveBeenCalledWith("hello world");
    expect(textarea.value).toBe("");
  });

  it("surfaces server errors inline without clearing the textarea", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockRejectedValue({ detail: "message must be at most 500 characters" });
    renderComposer({ currentUser: "alice", onSubmit });
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "anything");
    await user.click(screen.getByRole("button", { name: /post message/i }));
    expect(
      await screen.findByText(/message must be at most 500 characters/i),
    ).toBeInTheDocument();
    // textarea preserves the user's text so they don't lose what they typed
    expect(textarea.value).toBe("anything");
  });

  it("submits via Cmd+Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderComposer({ currentUser: "alice", onSubmit });
    await user.type(screen.getByRole("textbox"), "shortcut works");
    await user.keyboard("{Meta>}{Enter}{/Meta}");
    expect(onSubmit).toHaveBeenCalledWith("shortcut works");
  });
});
