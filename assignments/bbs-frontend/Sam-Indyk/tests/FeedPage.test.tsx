import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FeedPage } from "../src/pages/FeedPage";
import type { Post } from "../src/api/types";

const originalFetch = globalThis.fetch;

function postFixture(overrides: Partial<Post> = {}): Post {
  return {
    id: 1,
    username: "alice",
    message: "default",
    created_at: "2026-05-13T12:00:00",
    updated_at: null,
    reactions: {},
    ...overrides,
  };
}

describe("<FeedPage />", () => {
  beforeEach(() => {
    localStorage.setItem("bbs.username", "alice");
  });
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders posts returned by /posts", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify([
          postFixture({ id: 2, message: "second one" }),
          postFixture({ id: 1, message: "first one" }),
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    globalThis.fetch = fetchMock;

    render(
      <MemoryRouter>
        <FeedPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("second one")).toBeInTheDocument();
    expect(screen.getByText("first one")).toBeInTheDocument();
  });

  it("shows an error banner if the fetch fails", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => {
      throw new TypeError("fetch failed");
    });
    globalThis.fetch = fetchMock;

    render(
      <MemoryRouter>
        <FeedPage />
      </MemoryRouter>
    );

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Could not reach the server/i)).toBeInTheDocument();
  });

  it("submitting the search form sets the ?q= URL parameter and refetches", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
    );
    globalThis.fetch = fetchMock;

    render(
      <MemoryRouter initialEntries={["/"]}>
        <FeedPage />
      </MemoryRouter>
    );

    const input = await screen.findByPlaceholderText(/filter by message/i);
    const user = userEvent.setup();
    await user.type(input, "hello");
    await user.click(screen.getByRole("button", { name: /apply/i }));

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((c) => String(c[0]));
      expect(urls.some((u) => u.includes("q=hello"))).toBe(true);
    });
  });

  it("renders empty state when there are no posts", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
    );
    globalThis.fetch = fetchMock;

    render(
      <MemoryRouter>
        <FeedPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/no posts yet/i)).toBeInTheDocument();
  });
});
