import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { FeedView } from "../src/views/FeedView";
import * as postsApi from "../src/api/posts";
import { ApiError, type Post } from "../src/api/types";

function makePost(over: Partial<Post> & Pick<Post, "id" | "username" | "message">): Post {
  return {
    id: over.id,
    username: over.username,
    message: over.message,
    created_at: over.created_at ?? "2026-05-15T17:00:00",
    updated_at: over.updated_at ?? null,
  };
}

function renderFeed(currentUser = "alice") {
  return render(
    <MemoryRouter>
      <FeedView currentUser={currentUser} />
    </MemoryRouter>,
  );
}

describe("FeedView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("optimistically removes a deleted post and rolls back on server failure", async () => {
    const user = userEvent.setup();

    vi.spyOn(postsApi, "listPosts").mockResolvedValueOnce([
      makePost({ id: 1, username: "alice", message: "first post" }),
      makePost({ id: 2, username: "bob", message: "not mine" }),
    ]);
    vi.spyOn(postsApi, "deletePost").mockRejectedValueOnce(
      new ApiError(500, "database is locked"),
    );

    renderFeed("alice");

    await waitFor(() =>
      expect(screen.getByText("first post")).toBeInTheDocument(),
    );

    const deleteBtn = screen.getByRole("button", { name: /delete post 1/i });
    expect(
      screen.queryByRole("button", { name: /delete post 2/i }),
    ).not.toBeInTheDocument();

    await user.click(deleteBtn);

    await waitFor(() => {
      expect(screen.getByText(/database is locked/i)).toBeInTheDocument();
      expect(screen.getByText("first post")).toBeInTheDocument();
    });
  });
});
