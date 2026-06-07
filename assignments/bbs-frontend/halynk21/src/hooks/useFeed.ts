import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, buildCursor } from '../api/client';
import { api } from '../api/endpoints';
import type { PostOut } from '../api/types';
import { useToast } from '../context/ToastContext';
import { usePolling } from './usePolling';

const PAGE_SIZE = 20;
const POLL_MS = 5000;
const TOMBSTONE_TTL_MS = 30_000;

// Union by id, sort id DESC. Server returns id DESC and our list is sorted
// the same way; merging is just dedup + sort. On collision we prefer the
// fresh copy (it carries the latest updated_at, etc.).
function mergeUnion(existing: PostOut[], fresh: PostOut[]): PostOut[] {
  const byId = new Map<number, PostOut>();
  for (const p of existing) byId.set(p.id, p);
  for (const p of fresh) byId.set(p.id, p);
  return Array.from(byId.values()).sort((a, b) => b.id - a.id);
}

export type FeedHandle = {
  posts: PostOut[];
  loading: boolean;
  revalidating: boolean;
  loadingMore: boolean;
  error: ApiError | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  deletePost: (id: number) => Promise<boolean>;
  refetch: () => Promise<void>;
};

// Composite feed hook. Owns: fetch + 5s polling + tombstone-filtered merge +
// cursor-based load more + optimistic delete with rollback. Pages just call
// it and render — no fetch logic anywhere else.
export function useFeed({ q }: { q: string }): FeedHandle {
  const [posts, setPosts] = useState<PostOut[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [revalidating, setRevalidating] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [isFirstLoadComplete, setIsFirstLoadComplete] = useState<boolean>(false);

  const tombstonesRef = useRef<Set<number>>(new Set());
  const tombstoneTimersRef = useRef<Map<number, number>>(new Map());
  const abortRef = useRef<AbortController | null>(null);
  const loadMoreAbortRef = useRef<AbortController | null>(null);
  const postsRef = useRef<PostOut[]>(posts);
  useEffect(() => {
    postsRef.current = posts;
  });

  const { toast } = useToast();

  const doFetch = useCallback(
    async (mode: 'replace' | 'merge'): Promise<void> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // "loading" only when no data on screen; "revalidating" otherwise.
      if (postsRef.current.length === 0) setLoading(true);
      else setRevalidating(true);

      try {
        const fresh = await api.listRecent(
          { q: q || undefined, limit: PAGE_SIZE },
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        const filtered = fresh.filter((p) => !tombstonesRef.current.has(p.id));

        setPosts((prev) =>
          mode === 'replace' ? filtered : mergeUnion(prev, filtered),
        );
        setError(null);
        // hasMore is conservative: if we got a full page back, there might be older.
        if (mode === 'replace') setHasMore(fresh.length >= PAGE_SIZE);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (controller.signal.aborted) return;
        setError(
          err instanceof ApiError
            ? err
            : new ApiError(0, err instanceof Error ? err.message : 'Network error'),
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          setRevalidating(false);
          setIsFirstLoadComplete(true);
        }
      }
    },
    [q],
  );

  // q change (and initial mount): replace.
  useEffect(() => {
    void doFetch('replace');
    return () => {
      abortRef.current?.abort();
      loadMoreAbortRef.current?.abort();
    };
  }, [doFetch]);

  // Polling: merge mode, only after first load completes.
  const pollRefetch = useCallback(() => doFetch('merge'), [doFetch]);
  usePolling(pollRefetch, { ms: POLL_MS, enabled: isFirstLoadComplete });

  const loadMore = useCallback(async (): Promise<void> => {
    if (loadingMore || !hasMore || postsRef.current.length === 0) return;

    loadMoreAbortRef.current?.abort();
    const controller = new AbortController();
    loadMoreAbortRef.current = controller;

    setLoadingMore(true);
    const lastId = postsRef.current[postsRef.current.length - 1].id;
    const cursor = buildCursor(lastId);

    try {
      const page = await api.listPage(
        { q: q || undefined, limit: PAGE_SIZE, cursor },
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      const filtered = page.posts.filter((p) => !tombstonesRef.current.has(p.id));
      setPosts((prev) => mergeUnion(prev, filtered));
      setHasMore(page.next_cursor !== null);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const msg = err instanceof ApiError ? err.message : 'Failed to load more.';
      toast('error', msg);
    } finally {
      if (!controller.signal.aborted) setLoadingMore(false);
    }
  }, [q, hasMore, loadingMore, toast]);

  const deletePost = useCallback(
    async (id: number): Promise<boolean> => {
      // Short-circuit duplicate clicks while a delete is in flight. The
      // tombstone is added synchronously below, so a second click in the
      // same render tick (or before postsRef updates) sees it and bails
      // without firing a second DELETE.
      if (tombstonesRef.current.has(id)) return true;

      const target = postsRef.current.find((p) => p.id === id);
      if (!target) return true;

      // Optimistic remove + tombstone (so the next poll doesn't resurrect it).
      setPosts((prev) => prev.filter((p) => p.id !== id));
      tombstonesRef.current.add(id);
      const timerId = window.setTimeout(() => {
        tombstonesRef.current.delete(id);
        tombstoneTimersRef.current.delete(id);
      }, TOMBSTONE_TTL_MS);
      tombstoneTimersRef.current.set(id, timerId);

      try {
        await api.deletePost(id);
        return true;
      } catch (err) {
        // 404 means the post was already gone server-side — e.g. another
        // tab won the delete race. The optimistic removal was correct, so
        // keep it (and keep the tombstone); just tell the user it took
        // effect. Rolling back here would resurrect a ghost that polling
        // can't clear, since the server no longer returns the post.
        if (err instanceof ApiError && err.status === 404) {
          toast('info', 'That post was already gone.');
          return true;
        }
        // Real failure: roll back — drop the tombstone, re-insert at the
        // right id-DESC position.
        const t = tombstoneTimersRef.current.get(id);
        if (t !== undefined) window.clearTimeout(t);
        tombstoneTimersRef.current.delete(id);
        tombstonesRef.current.delete(id);
        setPosts((prev) => mergeUnion(prev, [target]));
        const msg = err instanceof ApiError ? err.message : "Couldn't delete that post.";
        toast('error', `${msg} It's back.`);
        return false;
      }
    },
    [toast],
  );

  const refetch = useCallback(() => doFetch('replace'), [doFetch]);

  return {
    posts,
    loading,
    revalidating,
    loadingMore,
    error,
    hasMore,
    loadMore,
    deletePost,
    refetch,
  };
}
