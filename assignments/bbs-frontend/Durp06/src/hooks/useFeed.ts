import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, listPosts } from '../api/bbs';
import type { Post } from '../api/bbs';

interface UseFeedArgs {
  q?: string;
  username?: string;
  pageSize?: number;
  pollMs?: number;
}

interface FeedState {
  posts: Post[];
  loading: boolean;
  error: string | null;
  nextOffset: number | null;
  loadMore: () => Promise<void>;
  loadingMore: boolean;
  refetch: () => Promise<void>;
  // Local mutations (used by FeedPage's optimistic delete).
  removeById: (id: number) => void;
  restore: (post: Post, atIndex: number) => void;
  // Optimistic-delete bookkeeping: while a delete is in flight, the consumer
  // marks the id as "pending delete" so the next poll's response doesn't
  // resurrect it. Cleared on either confirm or rollback.
  markPendingDelete: (id: number) => void;
  clearPendingDelete: (id: number) => void;
}

const DEFAULT_PAGE_SIZE = 20;
const DEFAULT_POLL_MS = 5000;

// The feed is the only hook that polls. Polling pauses when the tab is hidden
// (no point fetching for a user who isn't looking) and resumes on focus.
export function useFeed({
  q,
  username,
  pageSize = DEFAULT_PAGE_SIZE,
  pollMs = DEFAULT_POLL_MS,
}: UseFeedArgs = {}): FeedState {
  const [posts, setPosts] = useState<Post[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs (not state) so reads inside pollOnce don't need re-rendering and the
  // callback identity stays stable across renders.
  const argsRef = useRef({ q, username, pageSize });
  argsRef.current = { q, username, pageSize };
  const pendingDeletesRef = useRef<Set<number>>(new Set());
  const postsRef = useRef<Post[]>(posts);
  postsRef.current = posts;

  const fetchInitial = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listPosts({
        q: argsRef.current.q,
        username: argsRef.current.username,
        limit: argsRef.current.pageSize,
        offset: 0,
      });
      setPosts(page.posts);
      setNextOffset(page.nextCursor === null ? null : Number(page.nextCursor));
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return;
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async () => {
    await fetchInitial();
  }, [fetchInitial]);

  // Polling fetch — separate path from `refetch` so it doesn't flip `loading`
  // (which would re-show the spinner every 5s). Refreshes whatever the user
  // has currently loaded so paginated content stays continuous when new posts
  // arrive at the head. Respects pending-delete ids so an optimistic delete
  // in flight isn't resurrected by a poll that races it.
  const pollOnce = useCallback(async () => {
    try {
      const currentCount = postsRef.current.filter((p) => p.id >= 0).length;
      const limit = Math.max(argsRef.current.pageSize, currentCount);
      const page = await listPosts({
        q: argsRef.current.q,
        username: argsRef.current.username,
        limit,
        offset: 0,
      });
      const pendingDeletes = pendingDeletesRef.current;
      // `page.posts` only ever holds server-assigned (positive) ids; the
      // pending-delete set is only populated with positive ids (FeedPage's
      // handleDelete passes `post.id` which is positive for any row the
      // server returned). Optimistic-create posts (negative ids) live in
      // `current` and are spliced back below — they're untouched by this
      // filter regardless of the pending-delete set's contents.
      const fresh = pendingDeletes.size === 0
        ? page.posts
        : page.posts.filter((p) => !pendingDeletes.has(p.id));
      setPosts((current) => {
        const optimistic = current.filter((p) => p.id < 0);
        return [...optimistic, ...fresh];
      });
      setError(null);
    } catch {
      // Deliberate broad swallow — `listPosts` doesn't take a signal here so
      // an AbortError can't occur; the only failures we'd see are network /
      // server hiccups. Initial-load errors surface via `error`; background
      // poll failures shouldn't hijack the UI with a toast storm.
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (nextOffset === null || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await listPosts({
        q: argsRef.current.q,
        username: argsRef.current.username,
        limit: argsRef.current.pageSize,
        offset: nextOffset,
      });
      // Offset pagination can return rows the user already has if new posts
      // were inserted at the head between clicks — dedupe.
      setPosts((current) => {
        const known = new Set(current.map((p) => p.id));
        const fresh = page.posts.filter((p) => !known.has(p.id));
        return [...current, ...fresh];
      });
      setNextOffset(page.nextCursor === null ? null : Number(page.nextCursor));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }, [nextOffset, loadingMore]);

  // Initial load + refetch on query change.
  useEffect(() => {
    void fetchInitial();
  }, [fetchInitial, q, username, pageSize]);

  // Polling. Reset every time the query changes so the interval closure is fresh.
  // Pause polling while the tab is hidden.
  useEffect(() => {
    if (pollMs <= 0) return;
    let id: number | undefined;
    const start = () => {
      stop();
      id = window.setInterval(() => {
        if (!document.hidden) void pollOnce();
      }, pollMs);
    };
    const stop = () => {
      if (id !== undefined) window.clearInterval(id);
      id = undefined;
    };
    const onVisibility = () => {
      if (document.hidden) stop();
      else {
        void pollOnce();
        start();
      }
    };
    start();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [pollMs, pollOnce, q, username, pageSize]);

  const removeById = useCallback(
    (id: number) => setPosts((cur) => cur.filter((p) => p.id !== id)),
    [],
  );
  const restore = useCallback((post: Post, atIndex: number) => {
    setPosts((cur) => {
      const next = cur.slice();
      next.splice(Math.max(0, Math.min(atIndex, next.length)), 0, post);
      return next;
    });
  }, []);

  const markPendingDelete = useCallback((id: number) => {
    pendingDeletesRef.current.add(id);
  }, []);
  const clearPendingDelete = useCallback((id: number) => {
    pendingDeletesRef.current.delete(id);
  }, []);

  return {
    posts,
    loading,
    error,
    nextOffset,
    loadMore,
    loadingMore,
    refetch,
    removeById,
    restore,
    markPendingDelete,
    clearPendingDelete,
  };
}
