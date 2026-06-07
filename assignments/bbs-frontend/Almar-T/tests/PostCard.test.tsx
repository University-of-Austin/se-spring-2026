import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { PostCard } from "../src/components/PostCard";
import { ToastProvider } from "../src/hooks/useToast";
import type { Post } from "../src/api/types";

const sample: Post = {
  id: 42,
  username: "alice",
  message: "hello world",
  created_at: "2024-01-01T12:00:00",
  updated_at: null,
  board: "general",
};

function renderCard(overrides: Partial<Parameters<typeof PostCard>[0]> = {}) {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <PostCard
          post={sample}
          currentUser={null}
          showReactions={false}
          {...overrides}
        />
      </ToastProvider>
    </MemoryRouter>,
  );
}

describe("PostCard", () => {
  it("renders the message and a username link", () => {
    renderCard();
    expect(screen.getByText("hello world")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "@alice" });
    expect(link).toHaveAttribute("href", "/users/alice");
  });

  it("shows an (edited) marker when updated_at is set", () => {
    renderCard({ post: { ...sample, updated_at: "2024-01-02T12:00:00" } });
    expect(screen.getByText(/edited/i)).toBeInTheDocument();
  });

  it("calls onDelete with the post when the delete button is clicked", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    renderCard({ onDelete, currentUser: "alice" });
    await user.click(screen.getByRole("button", { name: /delete post 42/i }));
    expect(onDelete).toHaveBeenCalledWith(sample);
  });

  it("marks the card as busy when optimistic and hides the delete button", () => {
    const onDelete = vi.fn();
    renderCard({ post: sample, onDelete, optimistic: true });
    const card = screen.getByRole("article");
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(
      screen.queryByRole("button", { name: /delete/i }),
    ).not.toBeInTheDocument();
  });

  it("warns when the current user is not the post author", () => {
    renderCard({ onDelete: vi.fn(), currentUser: "bob" });
    expect(screen.getByText(/not your post/i)).toBeInTheDocument();
  });
});
