import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Post } from "../api/client";
import { deletePost, listPosts } from "../api/posts";
import { useAuth } from "../auth/AuthContext";
import { Compose } from "../components/Compose";
import { ErrorBanner } from "../components/ErrorBanner";
import { PostCard } from "../components/PostCard";
import { Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { FOCUS_SEARCH_EVENT } from "../components/Layout";
import { usePolling } from "../hooks/usePolling";

const PAGE_SIZE = 20;
const POLL_MS = 5000;

export function FeedPage() {
  const { username } = useAuth();
  const { push } = useToast();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set());
  const searchRef = useRef<HTMLInputElement | null>(null);
  const queryRef = useRef(q);
  queryRef.current = q;

  const fetchInitial = useCallback(
    async (signal?: AbortSignal, search: string = "") => {
      setLoading(true);
      setError(null);
      try {
        const data = await listPosts({ q: search || undefined, limit: PAGE_SIZE, offset: 0 }, signal);
        const sorted = [...data].sort((a, b) => b.id - a.id);
        setPosts(sorted);
        setHasMore(data.length === PAGE_SIZE);
      } catch (err) {
        if ((err as { name?: string })?.name === "AbortError") return;
        setError(err instanceof ApiError ? err.message : "Failed to load feed");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // initial + on-search load
  useEffect(() => {
    const c = new AbortController();
    fetchInitial(c.signal, q);
    return () => c.abort();
  }, [q, fetchInitial]);

  // poll for new posts every 5s
  const pollLatest = useCallback(async () => {
    try {
      const latest = await listPosts({ q: queryRef.current || undefined, limit: PAGE_SIZE, offset: 0 });
      setPosts((prev) => {
        const real = prev.filter((p) => p.id > 0);
        const knownIds = new Set(real.map((p) => p.id));
        const fresh = latest.filter((p) => !knownIds.has(p.id));
        if (fresh.length === 0) return prev;
        const optimistic = prev.filter((p) => p.id < 0);
        const merged = [...fresh, ...real].sort((a, b) => b.id - a.id);
        return [...optimistic, ...merged];
      });
    } catch {
      // poll errors are silent; the main load handles the UI error state
    }
  }, []);
  usePolling(pollLatest, POLL_MS, !loading && !error);

  // focus search via '/' keyboard shortcut
  useEffect(() => {
    const handler = () => searchRef.current?.focus();
    window.addEventListener(FOCUS_SEARCH_EVENT, handler);
    return () => window.removeEventListener(FOCUS_SEARCH_EVENT, handler);
  }, []);

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setQ(searchInput.trim());
  }

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const offset = posts.filter((p) => p.id > 0).length;
      const next = await listPosts({ q: q || undefined, limit: PAGE_SIZE, offset });
      setPosts((prev) => {
        const ids = new Set(prev.map((p) => p.id));
        const fresh = next.filter((p) => !ids.has(p.id));
        return [...prev, ...fresh].sort((a, b) => b.id - a.id);
      });
      setHasMore(next.length === PAGE_SIZE);
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Failed to load more", "error");
    } finally {
      setLoadingMore(false);
    }
  }

  function addOptimistic(temp: Post) {
    setPosts((prev) => [temp, ...prev]);
    setPendingIds((s) => new Set(s).add(temp.id));
  }

  function rollback(tempId: number, msg: string) {
    setPosts((prev) => prev.filter((p) => p.id !== tempId));
    setPendingIds((s) => {
      const next = new Set(s);
      next.delete(tempId);
      return next;
    });
    push(msg, "error");
  }

  function reconcile(tempId: number, real: Post) {
    setPosts((prev) => {
      const without = prev.filter((p) => p.id !== tempId);
      return [real, ...without];
    });
    setPendingIds((s) => {
      const next = new Set(s);
      next.delete(tempId);
      return next;
    });
  }

  async function onDelete(id: number) {
    if (!username) return;
    const snapshot = posts;
    setPosts((prev) => prev.filter((p) => p.id !== id));
    setPendingIds((s) => new Set(s).add(id));
    try {
      await deletePost(id, username);
      push("Post deleted", "info");
    } catch (err) {
      setPosts(snapshot);
      const msg = err instanceof ApiError ? err.message : "Failed to delete";
      push(msg, "error");
    } finally {
      setPendingIds((s) => {
        const next = new Set(s);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="feed-page page">
      <section className="compose-wrap">
        <Compose
          onOptimistic={addOptimistic}
          onRollback={rollback}
          onReconcile={reconcile}
        />
      </section>

      <form className="search-row" onSubmit={onSearchSubmit} role="search">
        <label htmlFor="feed-search" className="visually-hidden">
          Search posts
        </label>
        <input
          ref={searchRef}
          id="feed-search"
          type="search"
          placeholder="Search posts… ( / to focus )"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit" className="btn">
          Search
        </button>
        {q && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setSearchInput("");
              setQ("");
            }}
          >
            Clear
          </button>
        )}
      </form>

      {loading && posts.length === 0 && <Spinner label="Loading feed…" />}
      {error && <ErrorBanner message={error} onRetry={() => fetchInitial(undefined, q)} />}
      {!loading && !error && posts.length === 0 && (
        <p className="empty-state">{q ? `No posts match "${q}".` : "No posts yet. Be the first."}</p>
      )}

      <ul className="post-list">
        {posts.map((p) => (
          <li key={p.id}>
            <PostCard
              post={p}
              showDelete={!!username && p.username === username && p.id > 0}
              onDelete={onDelete}
              pending={pendingIds.has(p.id) || p.id < 0}
            />
          </li>
        ))}
      </ul>

      {hasMore && !error && posts.length > 0 && (
        <div className="load-more-row">
          <button
            type="button"
            className="btn"
            onClick={loadMore}
            disabled={loadingMore}
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
