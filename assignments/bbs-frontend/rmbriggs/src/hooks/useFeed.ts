import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, BASE } from "@/api/client";
import type { ApiError, FeedPage, Post } from "@/api/types";

export type OptimisticPost = Post & { client_id: string; status: "pending" | "failed" };

export type FeedState = {
  posts: Post[];
  optimistic: OptimisticPost[];
  loading: boolean;
  error: ApiError | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refetch: () => Promise<void>;
  createPost: (message: string, board?: string | null, parent_id?: number | null) => Promise<void>;
};

export function useFeed(params?: { q?: string; board?: string; username?: string }): FeedState {
  const [posts, setPosts] = useState<Post[]>([]);
  const [optimistic, setOptimistic] = useState<OptimisticPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const isMounted = useRef(true);

  const buildQuery = useCallback(
    (cursor: string | null) => {
      const sp = new URLSearchParams();
      sp.set("limit", "20");
      sp.set("cursor", cursor ?? "");
      if (params?.q) sp.set("q", params.q);
      if (params?.board) sp.set("board", params.board);
      if (params?.username) sp.set("username", params.username);
      return sp.toString();
    },
    [params?.q, params?.board, params?.username],
  );

  const fetchFirstPage = useCallback(async () => {
    try {
      const data = await apiFetch<FeedPage>(`/posts?${buildQuery(null)}`);
      if (!isMounted.current) return;
      setPosts(data.posts);
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
      setError(null);
    } catch (e) {
      if (!isMounted.current) return;
      setError(e as ApiError);
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [buildQuery]);

  useEffect(() => {
    isMounted.current = true;
    setLoading(true);
    void fetchFirstPage();
    return () => {
      isMounted.current = false;
    };
  }, [fetchFirstPage]);

  useEffect(() => {
    const url = new URL(`${BASE}/posts/stream`);
    if (params?.board) url.searchParams.set("board", params.board);
    const es = new EventSource(url.toString());
    es.onmessage = () => void fetchFirstPage();
    return () => es.close();
  }, [fetchFirstPage, params?.board]);

  const loadMore = useCallback(async () => {
    if (!nextCursor) return;
    try {
      const data = await apiFetch<FeedPage>(`/posts?${buildQuery(nextCursor)}`);
      setPosts((prev) => {
        const seen = new Set(prev.map((p) => p.id));
        return [...prev, ...data.posts.filter((p) => !seen.has(p.id))];
      });
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (e) {
      setError(e as ApiError);
    }
  }, [nextCursor, buildQuery]);

  const createPost = useCallback(
    async (message: string, board: string | null = null, parent_id: number | null = null) => {
      const client_id = crypto.randomUUID();
      const username = localStorage.getItem("username") ?? "you";
      const draft: OptimisticPost = {
        client_id,
        status: "pending",
        id: -1,
        username,
        message,
        created_at: new Date().toISOString(),
        updated_at: null,
        board,
        parent_id,
        reaction_counts: {},
      };
      setOptimistic((prev) => [draft, ...prev]);
      try {
        const created = await apiFetch<Post>("/posts", {
          method: "POST",
          body: JSON.stringify({ message, board, parent_id }),
        });
        setOptimistic((prev) => prev.filter((p) => p.client_id !== client_id));
        setPosts((prev) => (prev.some((p) => p.id === created.id) ? prev : [created, ...prev]));
      } catch (e) {
        setOptimistic((prev) => prev.filter((p) => p.client_id !== client_id));
        throw e;
      }
    },
    [],
  );

  return { posts, optimistic, loading, error, hasMore, loadMore, refetch: fetchFirstPage, createPost };
}
