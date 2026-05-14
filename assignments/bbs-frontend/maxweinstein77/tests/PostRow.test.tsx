// Tests the PostRow component: renders post info, fires onDelete, links
// to author profile and post detail.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PostRow } from "../src/components/PostRow";
import { UsernameProvider } from "../src/hooks/useUsername";
import type { Post } from "../src/types";

const samplePost: Post = {
  id: 42,
  username: "alice",
  message: "hello world",
  created_at: new Date().toISOString(),
  updated_at: null,
};

// PostRow renders a ReactionButton which uses React Query + UsernameContext.
// Spin up a fresh QueryClient per test so caches don't bleed between cases.
function renderInApp(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <UsernameProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </UsernameProvider>
    </QueryClientProvider>,
  );
}

describe("PostRow", () => {
  it("renders the message, author link, and timestamp link", () => {
    renderInApp(<PostRow post={samplePost} />);
    expect(screen.getByText("hello world")).toBeInTheDocument();

    const authorLink = screen.getByRole("link", { name: "alice" });
    expect(authorLink).toHaveAttribute("href", "/users/alice");

    // The timestamp text varies ("just now", "5s ago", etc.); just check the link target.
    const allLinks = screen.getAllByRole("link");
    const postLink = allLinks.find((l) => l.getAttribute("href") === "/posts/42");
    expect(postLink).toBeDefined();
  });

  it("does not render a delete button when onDelete is not provided", () => {
    renderInApp(<PostRow post={samplePost} />);
    expect(screen.queryByRole("button", { name: /^delete/i })).toBeNull();
  });

  it("calls onDelete with the post id when the delete button is clicked", async () => {
    const onDelete = vi.fn();
    renderInApp(<PostRow post={samplePost} onDelete={onDelete} />);
    await userEvent.click(screen.getByRole("button", { name: /^delete/i }));
    expect(onDelete).toHaveBeenCalledWith(42);
  });
});
