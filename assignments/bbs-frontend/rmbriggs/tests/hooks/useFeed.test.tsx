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
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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

  it("test_useFeed_opens_event_stream_on_mount", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      respond({ posts: [], next_cursor: null, has_more: false }),
    );
    const constructed: string[] = [];
    class FakeES {
      onmessage: ((e: MessageEvent) => void) | null = null;
      constructor(public url: string) { constructed.push(url); }
      close() {}
    }
    vi.stubGlobal("EventSource", FakeES);

    const { result, unmount } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(constructed.length).toBe(1);
    expect(constructed[0]).toMatch(/\/posts\/stream$/);
    unmount();
  });

  it("test_useFeed_refetches_when_event_stream_emits_message", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(respond({ posts: [mkPost(1)], next_cursor: null, has_more: false }))
      .mockResolvedValue(respond({ posts: [mkPost(2), mkPost(1)], next_cursor: null, has_more: false }));

    let onMessage: ((e: MessageEvent) => void) | null = null;
    class FakeES {
      set onmessage(fn: (e: MessageEvent) => void) { onMessage = fn; }
      close() {}
      constructor(public url: string) {}
    }
    vi.stubGlobal("EventSource", FakeES);

    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.posts.map((p) => p.id)).toEqual([1]));

    await act(async () => {
      onMessage?.(new MessageEvent("message", { data: "tick" }));
    });

    await waitFor(() => expect(result.current.posts.map((p) => p.id)).toEqual([2, 1]));
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});
