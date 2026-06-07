import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { deletePost, listPosts } from "../api/posts";
import type { Post } from "../api/types";
import { ApiError } from "../api/types";
import { Loading, ErrorBlock } from "../components/StatusBlock";
import { PostRow } from "../components/PostRow";

const PAGE_SIZE = 20;

export function FeedView({ currentUser }: { currentUser: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlQ = searchParams.get("q") ?? "";

  const [qInput, setQInput] = useState(urlQ);
  const [posts, setPosts] = useState<Post[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setQInput(urlQ);
  }, [urlQ]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listPosts({ q: urlQ || undefined, limit: PAGE_SIZE, offset: 0 }).then(
      (data) => {
        if (cancelled) return;
        setPosts(data);
        setHasMore(data.length === PAGE_SIZE);
        setLoading(false);
      },
      (err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err : new ApiError(0, String(err)));
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [urlQ, reloadNonce]);

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    const next = qInput.trim();
    if (next) setSearchParams({ q: next });
    else setSearchParams({});
  }

  function clearSearch() {
    setQInput("");
    setSearchParams({});
  }

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const more = await listPosts({
        q: urlQ || undefined,
        limit: PAGE_SIZE,
        offset: posts.length,
      });
      setPosts((cur) => [...cur, ...more]);
      setHasMore(more.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, String(err)));
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleDelete(post: Post) {
    const prev = posts;
    setDeleteError(null);
    setPosts((cur) => cur.filter((p) => p.id !== post.id));
    try {
      await deletePost(post.id);
    } catch (err) {
      setPosts(prev);
      setDeleteError(
        err instanceof ApiError
          ? `Couldn't delete post ${post.id}: ${err.detail}`
          : `Couldn't delete post ${post.id}: ${String(err)}`,
      );
    }
  }

  return (
    <section className="view feed-view">
      <h1>Feed</h1>

      <form className="search" onSubmit={applySearch} role="search">
        <label htmlFor="feed-search" className="sr-only">
          Search posts
        </label>
        <input
          id="feed-search"
          ref={searchRef}
          type="search"
          placeholder="Search posts…"
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
        />
        <button type="submit" className="secondary">
          Search
        </button>
        {urlQ && (
          <button type="button" className="link-btn" onClick={clearSearch}>
            clear
          </button>
        )}
      </form>

      {urlQ && (
        <div className="muted small">
          Showing results for <strong>{urlQ}</strong>
        </div>
      )}

      {deleteError && (
        <div className="status error" role="alert">
          <div className="error-detail">{deleteError}</div>
        </div>
      )}

      {loading && <Loading />}
      {error && !loading && (
        <ErrorBlock
          error={error}
          onRetry={() => setReloadNonce((n) => n + 1)}
        />
      )}

      {!loading && !error && (
        <>
          {posts.length === 0 ? (
            <div className="empty">
              {urlQ ? "No posts match that search." : "No posts yet."}
            </div>
          ) : (
            <div className="post-list">
              {posts.map((p) => (
                <PostRow
                  key={p.id}
                  post={p}
                  canDelete={p.username === currentUser}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}

          {posts.length > 0 && (
            <div className="pager">
              <button
                type="button"
                className="secondary"
                disabled={!hasMore || loadingMore}
                onClick={loadMore}
              >
                {loadingMore
                  ? "Loading…"
                  : hasMore
                    ? "Load more"
                    : "End of feed"}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
