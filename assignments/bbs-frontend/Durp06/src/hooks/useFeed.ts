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
  // Local mutations (used by ComposePage optimistic create / FeedPage delete).
  prepend: (post: Post) => void;
  removeById: (id: number) => void;
  replaceById: (id: number, post: Post) => void;
  restore: (post: Post, atIndex: number) => void;
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

  const argsRef = useRef({ q, username, pageSize });
  argsRef.current = { q, username, pageSize };

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

  // Polling fetch is a *separate* path from refetch — it doesn't flip
  // `loading` (would re-show the spinner every 5s) and preserves any
  // already-loaded "load more" pages by only refreshing the head of the feed
  // when there are no extra pages loaded.
  const pollOnce = useCallback(async () => {
    try {
      const page = await listPosts({
        q: argsRef.current.q,
        username: argsRef.current.username,
        limit: argsRef.current.pageSize,
        offset: 0,
      });
      setPosts((current) => {
        // Preserve optimistic-create posts (negative ids) that haven't reconciled yet.
        const optimistic = current.filter((p) => p.id < 0);
        // If the user has paginated past the first page, splice the fresh head
        // in while keeping their lower pages untouched.
        const knownIds = new Set(page.posts.map((p) => p.id));
        const olderPages = current.filter((p) => p.id >= 0 && !knownIds.has(p.id));
        const olderBeyondFirstPage = olderPages.filter((p) => {
          // Anything older than the *last* post in the fresh first page stays.
          if (page.posts.length === 0) return true;
          return p.id < page.posts[page.posts.length - 1].id;
        });
        return [...optimistic, ...page.posts, ...olderBeyondFirstPage];
      });
      setError(null);
    } catch {
      // Swallow poll errors — initial load surfaces them via `error`; background poll failures
      // shouldn't hijack the UI.
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
      setPosts((current) => [...current, ...page.posts]);
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

  const prepend = useCallback((post: Post) => setPosts((cur) => [post, ...cur]), []);
  const removeById = useCallback(
    (id: number) => setPosts((cur) => cur.filter((p) => p.id !== id)),
    [],
  );
  const replaceById = useCallback(
    (id: number, post: Post) => setPosts((cur) => cur.map((p) => (p.id === id ? post : p))),
    [],
  );
  const restore = useCallback((post: Post, atIndex: number) => {
    setPosts((cur) => {
      const next = cur.slice();
      next.splice(Math.max(0, Math.min(atIndex, next.length)), 0, post);
      return next;
    });
  }, []);

  return {
    posts,
    loading,
    error,
    nextOffset,
    loadMore,
    loadingMore,
    refetch,
    prepend,
    removeById,
    replaceById,
    restore,
  };
}
