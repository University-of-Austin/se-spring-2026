import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ComposeView } from "../src/views/ComposeView";
import * as postsApi from "../src/api/posts";
import { ApiError } from "../src/api/types";

function renderCompose(username = "alice") {
  return render(
    <MemoryRouter>
      <ComposeView username={username} />
    </MemoryRouter>,
  );
}

describe("ComposeView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("disables Post when the textarea is empty and enables once you type", async () => {
    const user = userEvent.setup();
    renderCompose();

    const submit = screen.getByRole("button", { name: /post/i });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/new post message/i), "hi");
    expect(submit).toBeEnabled();
  });

  it("flips the char counter to the error class past 500 and marks the textarea invalid", async () => {
    const user = userEvent.setup();
    renderCompose();
    const textarea = screen.getByLabelText(/new post message/i);

    await user.click(textarea);
    await user.paste("x".repeat(501));

    expect(screen.getByText("501 / 500")).toHaveClass("err");
    expect(textarea).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("surfaces the server's 422 detail verbatim instead of a generic message", async () => {
    const user = userEvent.setup();
    vi.spyOn(postsApi, "createPost").mockRejectedValueOnce(
      new ApiError(422, "message must contain at least one non-whitespace character"),
    );
    renderCompose();

    await user.type(screen.getByLabelText(/new post message/i), "hello");
    await user.click(screen.getByRole("button", { name: /post/i }));

    await waitFor(() =>
      expect(
        screen.getByText(
          /message must contain at least one non-whitespace character/i,
        ),
      ).toBeInTheDocument(),
    );
  });
});
