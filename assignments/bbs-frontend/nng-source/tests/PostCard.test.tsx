import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { PostCard } from "../src/components/PostCard";
import type { Post } from "../src/types";

const basePost: Post = {
  id: 42,
  username: "bob",
  board: "general",
  message: "hello world",
  created_at: "2026-05-15T14:30:00",
  updated_at: null,
};

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("PostCard", () => {
  it("renders username, post id, and message", () => {
    wrap(<PostCard post={basePost} />);
    expect(screen.getByText("bob")).toBeInTheDocument();
    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("does not show a delete button by default", () => {
    wrap(<PostCard post={basePost} />);
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
  });

  it("shows a delete button when showDelete is true and calls onDelete with id", () => {
    const onDelete = vi.fn();
    wrap(<PostCard post={basePost} showDelete onDelete={onDelete} />);
    const btn = screen.getByRole("button", { name: /delete post 42/i });
    fireEvent.click(btn);
    expect(onDelete).toHaveBeenCalledWith(42);
  });

  it("marks the card aria-busy when it's an optimistic placeholder", () => {
    const optimistic = { ...basePost, id: -1 };
    wrap(<PostCard post={optimistic} optimistic />);
    const article = screen.getByRole("article");
    expect(article).toHaveAttribute("aria-busy", "true");
  });

  it("renders the edited marker when updated_at is set", () => {
    wrap(<PostCard post={{ ...basePost, updated_at: "2026-05-15T15:00:00" }} />);
    expect(screen.getByText(/edited/i)).toBeInTheDocument();
  });

  it("links the username to /users/<name>", () => {
    wrap(<PostCard post={basePost} />);
    const link = screen.getByRole("link", { name: "bob" });
    expect(link).toHaveAttribute("href", "/users/bob");
  });
});
