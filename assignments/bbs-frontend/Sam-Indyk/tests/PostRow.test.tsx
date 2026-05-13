import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PostRow } from "../src/components/PostRow";
import type { Post } from "../src/api/types";

const basePost: Post = {
  id: 7,
  username: "alice",
  message: "hello",
  created_at: new Date(Date.now() - 90_000).toISOString(),
  updated_at: null,
  reactions: {},
};

describe("<PostRow />", () => {
  it("renders message, author link, and detail link", () => {
    render(
      <MemoryRouter>
        <PostRow post={basePost} />
      </MemoryRouter>
    );
    expect(screen.getByText("hello")).toBeInTheDocument();

    const authorLink = screen.getByRole("link", { name: "alice" });
    expect(authorLink).toHaveAttribute("href", "/users/alice");

    const detailLink = screen.getByRole("link", { name: /view #7/ });
    expect(detailLink).toHaveAttribute("href", "/posts/7");
  });

  it("shows the pending tag and hides the detail link when pending", () => {
    render(
      <MemoryRouter>
        <PostRow post={basePost} pending />
      </MemoryRouter>
    );
    expect(screen.getByText(/posting…/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /view #/ })).toBeNull();
    expect(screen.getByRole("article")).toHaveAttribute("aria-busy", "true");
  });

  it("shows (edited) when updated_at is set", () => {
    render(
      <MemoryRouter>
        <PostRow
          post={{ ...basePost, updated_at: new Date().toISOString() }}
        />
      </MemoryRouter>
    );
    expect(screen.getByText(/\(edited\)/)).toBeInTheDocument();
  });

  it("URL-encodes usernames with safe characters", () => {
    render(
      <MemoryRouter>
        <PostRow post={{ ...basePost, username: "user_42" }} />
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: "user_42" })).toHaveAttribute(
      "href",
      "/users/user_42"
    );
  });
});
