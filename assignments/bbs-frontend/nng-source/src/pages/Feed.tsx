import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Compose } from "../components/Compose";
import { ErrorBox } from "../components/ErrorBox";
import { PostCard } from "../components/PostCard";
import { Spinner } from "../components/Spinner";
import type { Post } from "../types";

const PAGE_SIZE = 25;
const POLL_INTERVAL_MS = 5000;

export function Feed() {
  const { username, token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";

  // Local input state so typing doesn't fire a request per keystroke.
  // We sync URL on submit/blur.
  const [searchInput, setSearchInput] = useState(q);
  useEffect(() => { setSearchInput(q); }, [q]);

  const [posts, setPosts] = useState<Post[]>([]);
  const [optimisticIds, setOptimisticIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [newCount, setNewCount] = useState(0);
  const isPolling = useRef(false);

  // ---- initial / search load -----------------------------------------------
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNewCount(0);
    try {
      const data = await api.listPosts({ q: q || undefined, limit: PAGE_SIZE, offset: 0 });
      setPosts(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load posts.");
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => { void load(); }, [load]);

  // ---- "load more" pagination ---------------------------------------------
  async function loadMore() {
    setLoadingMore(true);
    try {
      const oldestId = posts
        .filter((p) => p.id > 0)
        .reduce<number | null>((acc, p) => (acc === null || p.id < acc ? p.id : acc), null);
      // Use offset = number of confirmed (non-optimistic) posts already loaded.
      const offset = posts.filter((p) => p.id > 0).length;
      const more = await api.listPosts({ q: q || undefined, limit: PAGE_SIZE, offset });
      if (more.length === 0) {
        setHasMore(false);
      } else {
        setPosts((prev) => {
          const known = new Set(prev.map((p) => p.id));
          const fresh = more.filter((p) => !known.has(p.id));
          return [...prev, ...fresh];
        });
        if (more.length < PAGE_SIZE) setHasMore(false);
      }
      // oldestId is informational; offset-based pagination is fine here.
      void oldestId;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load more.");
    } finally {
      setLoadingMore(false);
    }
  }

  // ---- gold: polling for real-time-ish updates ----------------------------
  // Every POLL_INTERVAL_MS, fetch the head of the feed. If new posts appear
  // (by id), prepend them and flash a count badge so the user sees motion
  // even if they're not scrolled to the top.
  useEffect(() => {
    if (loading || error) return;
    const id = setInterval(async () => {
      if (isPolling.current) return;
      if (document.hidden) return;          // pause when tab is backgrounded
      isPolling.current = true;
      try {
        const head = await api.listPosts({ q: q || undefined, limit: PAGE_SIZE, offset: 0 });
        setPosts((prev) => {
          const knownIds = new Set(prev.filter((p) => p.id > 0).map((p) => p.id));
          const fresh = head.filter((p) => !knownIds.has(p.id));
          if (fresh.length === 0) return prev;
          // Drop the optimistic placeholder if the server now has the real one
          // (matched by username + message, latest-first).
          const stillOptimistic = prev.filter((p) => p.id < 0);
          const cleanPrev = stillOptimistic.length === 0
            ? prev
            : prev.filter((p) => {
                if (p.id > 0) return true;
                return !fresh.some((f) => f.username === p.username && f.message === p.message);
              });
          setNewCount((c) => c + fresh.length);
          return [...fresh, ...cleanPrev];
        });
      } catch { /* swallow polling errors; next tick will retry */ }
      finally { isPolling.current = false; }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [q, loading, error]);

  // ---- optimistic post handlers passed to Compose -------------------------
  function onOptimisticAdd(p: Post) {
    setPosts((prev) => [p, ...prev]);
    setOptimisticIds((s) => new Set(s).add(p.id));
  }
  function onConfirm(placeholderId: number, real: Post) {
    setPosts((prev) => prev.map((p) => (p.id === placeholderId ? real : p)));
    setOptimisticIds((s) => {
      const n = new Set(s);
      n.delete(placeholderId);
      return n;
    });
  }
  function onRollback(placeholderId: number) {
    setPosts((prev) => prev.filter((p) => p.id !== placeholderId));
    setOptimisticIds((s) => {
      const n = new Set(s);
      n.delete(placeholderId);
      return n;
    });
  }

  // ---- delete handler (uses optimistic removal + rollback) ----------------
  async function onDelete(id: number) {
    if (!token) return;
    const snapshot = posts;
    setPosts((prev) => prev.filter((p) => p.id !== id));
    try {
      await api.deletePost(id, token);
    } catch (err) {
      setPosts(snapshot);
      setError(err instanceof Error ? err.message : "Could not delete that post.");
    }
  }

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSearchParams(searchInput ? { q: searchInput } : {}, { replace: false });
  }

  return (
    <div className="page page-feed">
      <section className="feed-search-section" aria-label="Search">
        <form onSubmit={onSearchSubmit} role="search">
          <label htmlFor="feed-search" className="visually-hidden">Search posts</label>
          <input
            id="feed-search"
            type="search"
            placeholder='Search posts... ("/" to focus)'
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary">Search</button>
          {q && (
            <button
              type="button"
              className="btn btn-link"
              onClick={() => setSearchParams({})}
            >
              Clear
            </button>
          )}
        </form>
        {q && <p className="feed-search-context">Showing results for <em>"{q}"</em></p>}
      </section>

      {username && (
        <section aria-label="Compose">
          <Compose
            onOptimisticAdd={onOptimisticAdd}
            onConfirm={onConfirm}
            onRollback={onRollback}
          />
        </section>
      )}

      {newCount > 0 && (
        <div className="new-posts-pill" role="status" aria-live="polite">
          {newCount} new {newCount === 1 ? "post" : "posts"} above
        </div>
      )}

      {loading ? (
        <Spinner label="Loading feed..." />
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : posts.length === 0 ? (
        <p className="empty-state">{q ? "No matching posts." : "No posts yet. Be the first."}</p>
      ) : (
        <>
          <ul className="post-list" aria-label="Posts">
            {posts.map((p) => (
              <li key={p.id < 0 ? `temp-${p.id}` : p.id}>
                <PostCard
                  post={p}
                  optimistic={optimisticIds.has(p.id)}
                  showDelete={!!username && p.username === username}
                  onDelete={onDelete}
                />
              </li>
            ))}
          </ul>
          {hasMore && (
            <div className="load-more-wrap">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={loadingMore}
                onClick={loadMore}
              >
                {loadingMore ? "Loading..." : "Load more"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
