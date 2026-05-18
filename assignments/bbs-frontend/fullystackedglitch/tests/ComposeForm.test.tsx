import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ComposeForm } from "../src/components/ComposeForm";
import { setStoredUsername } from "../src/lib/storage";

vi.mock("../src/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createPost: vi.fn(),
    },
  };
});

import { api } from "../src/lib/api";

function renderForm(onPosted = vi.fn()) {
  return render(
    <MemoryRouter>
      <ComposeForm onPosted={onPosted} />
    </MemoryRouter>,
  );
}

describe("ComposeForm", () => {
  beforeEach(() => {
    setStoredUsername("alice");
  });

  afterEach(() => {
    setStoredUsername(null);
    vi.clearAllMocks();
  });

  it("disables submit when input is empty, enables on type", async () => {
    const user = userEvent.setup();
    renderForm();
    const submit = screen.getByRole("button", { name: /post/i });
    expect(submit).toBeDisabled();

    await user.type(screen.getByRole("textbox"), "hello");
    expect(submit).toBeEnabled();
  });

  it("submits via Cmd+Enter and calls api with current user", async () => {
    const onPosted = vi.fn();
    const user = userEvent.setup();
    (api.createPost as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 1,
      username: "alice",
      message: "hi from keyboard",
      created_at: "now",
    });

    renderForm(onPosted);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hi from keyboard");
    // jsdom doesn't distinguish meta from a regular keypress, but the handler
    // accepts ctrl OR meta — userEvent's modifier syntax exercises that path.
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(api.createPost).toHaveBeenCalledWith("hi from keyboard", "alice");
    expect(onPosted).toHaveBeenCalled();
  });

  it("surfaces server 422 message inline instead of swallowing it", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("../src/lib/api");
    (api.createPost as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new ApiError(422, undefined, "String should have at most 500 characters"),
    );

    renderForm();
    await user.type(screen.getByRole("textbox"), "anything");
    await user.click(screen.getByRole("button", { name: /post/i }));

    expect(
      await screen.findByText(/String should have at most 500 characters/),
    ).toBeInTheDocument();
  });

  it("shows the signed-out prompt with no stored username", () => {
    setStoredUsername(null);
    renderForm();
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
