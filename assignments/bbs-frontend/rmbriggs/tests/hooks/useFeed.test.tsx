import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useFeed } from "@/hooks/useFeed";
import type { Post } from "@/api/types";

const mkPost = (id: number): Post => ({
  id, username: "alice", message: `m${id}`, created_at: "2026-05-13T00:00:00",
  updated_at: null, board: null, parent_id: null, reaction_counts: {},
});

const respond = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("useFeed", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.restoreAllMocks();
  });

  it("test_useFeed_starts_in_loading_state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useFeed());
    expect(result.current.loading).toBe(true);
  });

  it("test_useFeed_transitions_to_success_with_posts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      respond({ posts: [mkPost(1), mkPost(2)], next_cursor: null, has_more: false }),
    );
    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.posts.map((p) => p.id)).toEqual([1, 2]);
  });

  it("test_useFeed_transitions_to_error_on_500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(respond({ detail: "boom" }, 500));
    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatchObject({ status: 500 });
  });

  it("test_useFeed_loadMore_appends_with_cursor", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(respond({ posts: [mkPost(2)], next_cursor: "c1", has_more: true }))
      .mockResolvedValueOnce(respond({ posts: [mkPost(1)], next_cursor: null, has_more: false }));

    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.posts.length).toBe(1));
    await act(async () => { await result.current.loadMore(); });
    expect(result.current.posts.map((p) => p.id)).toEqual([2, 1]);
    expect(result.current.hasMore).toBe(false);
    expect(fetchMock.mock.calls[1][0]).toContain("cursor=c1");
  });

  it("test_useFeed_polls_every_3s_and_merges_new_posts", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(respond({ posts: [mkPost(1)], next_cursor: null, has_more: false }))
      .mockResolvedValue(respond({ posts: [mkPost(2), mkPost(1)], next_cursor: null, has_more: false }));

    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.posts.length).toBe(1));

    await act(async () => { await vi.advanceTimersByTimeAsync(3001); });

    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(result.current.posts.map((p) => p.id)).toEqual([2, 1]);
  });
});
