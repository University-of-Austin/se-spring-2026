import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ComposeForm } from "../components/ComposeForm";
import { Pagination } from "../components/Pagination";
import { PostRow } from "../components/PostRow";
import {
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
} from "../components/StatusBlock";
import { useApi } from "../hooks/useApi";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { ApiError, api } from "../lib/api";
import type { Post } from "../lib/types";
import styles from "./FeedView.module.css";

const PAGE_SIZE = 10;
const POLL_INTERVAL_MS = 5000;

export function FeedView() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? "1"));
  const offset = (page - 1) * PAGE_SIZE;

  const searchId = useId();
  const searchRef = useRef<HTMLInputElement>(null);
  const [searchInput, setSearchInput] = useState(q);

  // Keep the input in sync if URL changes externally (eg back button).
  useEffect(() => {
    setSearchInput(q);
  }, [q]);

  // Debounced URL sync — typing pushes to URL after 300ms idle. The fetch
  // depends on URL, so this is what triggers the new request.
  useEffect(() => {
    if (searchInput === q) return;
    const t = setTimeout(() => {
      const next = new URLSearchParams(params);
      if (searchInput) next.set("q", searchInput);
      else next.delete("q");
      next.delete("page"); // reset to page 1 when query changes
      setParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput, q, params, setParams]);

  useKeyboardShortcuts([
    {
      key: "/",
      handler: (e) => {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      },
    },
  ]);

  const key = `feed:${q}:${offset}:${PAGE_SIZE}`;
  const fetcher = useCallback(
    (signal: AbortSignal) =>
      api.listPosts({ q, offset, limit: PAGE_SIZE }, signal),
    [q, offset],
  );
  const { data, loading, error, refetch } = useApi(fetcher, key);

  // Local mirror used for optimistic delete. Server data is the source of
  // truth — whenever it arrives, we reset the local mirror.
  const [localPosts, setLocalPosts] = useState<Post[]>([]);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());
  const [rollbackMsg, setRollbackMsg] = useState<string | null>(null);

  useEffect(() => {
    if (data) setLocalPosts(data);
  }, [data]);

  // Gold: background polling for real-time-ish updates. Every POLL_INTERVAL_MS
  // we refetch the current page silently (no loading spinner, no error toast)
  // and merge results into localPosts. The ref dance lets the interval read
  // the current deletingIds without being recreated every time the Set
  // changes — otherwise we'd churn the timer on every optimistic delete and
  // never actually poll.
  const deletingIdsRef = useRef(deletingIds);
  deletingIdsRef.current = deletingIds;

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState !== "visible") return;
      api
        .listPosts({ q, offset, limit: PAGE_SIZE })
        .then((fresh) => {
          // Don't resurrect a post that's mid-delete: the user has already
          // seen it disappear, and the server might not have caught up yet.
          setLocalPosts(
            fresh.filter((p) => !deletingIdsRef.current.has(p.id)),
          );
        })
        .catch(() => {
          // Silent: a failed poll doesn't need to surface to the user. The
          // next initial-fetch refetch (or manual retry) will if it persists.
        });
    };
    const interval = setInterval(tick, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [q, offset]);

  const onDelete = async (post: Post) => {
    if (deletingIds.has(post.id)) return;
    setRollbackMsg(null);
    const snapshot = localPosts;
    // Optimistic: remove immediately, then call the API. If it fails, restore.
    setLocalPosts((prev) => prev.filter((p) => p.id !== post.id));
    setDeletingIds((prev) => new Set(prev).add(post.id));
    try {
      await api.deletePost(post.id);
    } catch (e) {
      setLocalPosts(snapshot);
      const msg =
        e instanceof ApiError ? e.message : (e as Error).message ?? "Delete failed";
      setRollbackMsg(`Couldn't delete: ${msg}`);
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(post.id);
        return next;
      });
    }
  };

  const onPosted = (post: Post) => {
    // If we're on page 1 with no filter, prepend optimistically so it shows
    // up without a round trip. Otherwise just refetch the current view.
    if (page === 1 && !q) {
      setLocalPosts((prev) => [post, ...prev.slice(0, PAGE_SIZE - 1)]);
    } else {
      refetch();
    }
  };

  const goToPage = (p: number) => {
    const next = new URLSearchParams(params);
    if (p <= 1) next.delete("page");
    else next.set("page", String(p));
    setParams(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // hasNext: if the page is full, assume more exist. False positives are
  // recoverable (Next yields an empty page); false negatives are not.
  const hasNext = (data?.length ?? 0) === PAGE_SIZE;

  return (
    <section className={styles.section}>
      <ComposeForm onPosted={onPosted} />

      <form
        className={styles.searchRow}
        role="search"
        onSubmit={(e) => e.preventDefault()}
      >
        <label htmlFor={searchId} className={styles.searchLabel}>
          search
        </label>
        <input
          id={searchId}
          ref={searchRef}
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="filter messages…  (press /)"
          aria-label="Search messages"
        />
        {q && (
          <button
            type="button"
            className={styles.clearBtn}
            onClick={() => setSearchInput("")}
          >
            clear
          </button>
        )}
      </form>

      {rollbackMsg && (
        <div className={styles.rollbackBanner} role="alert">
          {rollbackMsg}
        </div>
      )}

      {loading && localPosts.length === 0 && <LoadingBlock label="Loading feed" />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}

      {!loading && !error && localPosts.length === 0 && (
        <EmptyBlock>
          {q ? `no posts match "${q}"` : "no posts yet — be first."}
        </EmptyBlock>
      )}

      <div className={styles.list}>
        {localPosts.map((p) => (
          <PostRow
            key={p.id}
            post={p}
            onDelete={onDelete}
            deleting={deletingIds.has(p.id)}
          />
        ))}
      </div>

      {(page > 1 || hasNext) && (
        <Pagination page={page} hasNext={hasNext} onChange={goToPage} />
      )}
    </section>
  );
}
