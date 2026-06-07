import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { Post } from "../api/types";
import { Compose } from "../components/Compose";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { PostRow } from "../components/PostRow";
import { Spinner } from "../components/Spinner";
import { ToastRow } from "../components/Toast";
import { useApi } from "../hooks/useApi";
import { usePolling } from "../hooks/usePolling";
import { useToasts } from "../hooks/useToasts";
import { useUser } from "../hooks/useUser";

const PAGE_SIZE = 10;
const POLL_INTERVAL_MS = 5000;

export function FeedPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const qFromUrl = searchParams.get("q") ?? "";
  const [searchInput, setSearchInput] = useState(qFromUrl);
  const [page, setPage] = useState(0);
  const [pendingPosts, setPendingPosts] = useState<Post[]>([]);
  const { username } = useUser();
  const { toasts, push, dismiss } = useToasts();

  // Reset page when the URL query changes.
  useEffect(() => {
    setSearchInput(qFromUrl);
    setPage(0);
  }, [qFromUrl]);

  const limit = (page + 1) * PAGE_SIZE;

  const { data, loading, error, refetch, setData } = useApi(
    (signal) => api.listPosts({ q: qFromUrl || undefined, limit }, signal),
    [qFromUrl, limit]
  );

  // Poll for new posts every 5s — only when there's no active search filter
  // so we don't fight the user's typing.
  usePolling(refetch, POLL_INTERVAL_MS, !qFromUrl);

  const visible = useMemo(() => {
    if (!data) return [];
    // Optimistic posts go on top; filter out any whose real twin already
    // landed in `data` (matched by message + username + within 30s).
    const filteredPending = pendingPosts.filter(
      (p) =>
        !data.some(
          (real) =>
            real.username === p.username &&
            real.message === p.message &&
            Math.abs(
              new Date(real.created_at).getTime() -
                new Date(p.created_at).getTime()
            ) < 30000
        )
    );
    return [...filteredPending, ...data];
  }, [data, pendingPosts]);

  const onOptimistic = useCallback((pending: Post) => {
    setPendingPosts((prev) => [pending, ...prev]);
  }, []);

  const onSettled = useCallback(
    (
      result:
        | { ok: true; post: Post; pendingId: number }
        | { ok: false; error: ApiError; pendingId: number }
    ) => {
      // Drop the optimistic placeholder; the real post (if any) will land
      // via the next refetch.
      setPendingPosts((prev) => prev.filter((p) => p.id !== result.pendingId));
      if (result.ok) {
        // Insert immediately so the UI is responsive even before polling.
        setData((current) => (current ? [result.post, ...current] : [result.post]));
        push("Posted.");
      } else {
        push(`Could not post: ${result.error.message}`, "danger");
      }
    },
    [push, setData]
  );

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchParams(searchInput ? { q: searchInput } : {});
  }

  function clearSearch() {
    setSearchInput("");
    setSearchParams({});
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Feed</h1>
          <div className="sub">
            Newest posts first.{" "}
            {!qFromUrl && username && (
              <>
                Updates every {POLL_INTERVAL_MS / 1000}s while this tab is open.
              </>
            )}
          </div>
        </div>
      </div>

      <Compose onOptimistic={onOptimistic} onSettled={onSettled} />

      <div className="section-divider" />

      <form className="toolbar" onSubmit={applySearch} role="search">
        <label htmlFor="feed-search" className="field-label" style={{ marginRight: 0 }}>
          Search
        </label>
        <input
          id="feed-search"
          className="input"
          type="search"
          placeholder="filter by message text…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit" className="btn">
          Apply
        </button>
        {qFromUrl && (
          <button type="button" className="btn btn-ghost" onClick={clearSearch}>
            Clear
          </button>
        )}
      </form>

      {error && <ErrorBanner error={error} onRetry={refetch} />}

      {loading && !data && <Spinner label="Loading feed" />}

      {data && visible.length === 0 && !loading && (
        <EmptyState
          title={qFromUrl ? "Nothing matches that search" : "No posts yet"}
          description={
            qFromUrl
              ? "Try a different word, or clear the filter."
              : "Be the first to post."
          }
          action={
            !username ? (
              <Link to="/auth" className="btn btn-primary">
                Sign in to post
              </Link>
            ) : null
          }
        />
      )}

      {visible.length > 0 && (
        <div className="post-list" aria-live="polite">
          {visible.map((p) => (
            <PostRow key={p.id} post={p} pending={p.id < 0} />
          ))}
        </div>
      )}

      {data && data.length === limit && (
        <div className="pager">
          <button
            type="button"
            className="btn"
            onClick={() => setPage((p) => p + 1)}
            disabled={loading}
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        </div>
      )}

      <ToastRow toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
