// Feed view, silver tier.
//
// Two things make this view richer than the bronze cut:
//
//   1. Infinite scroll.  A sentinel <div> at the bottom of the list
//      is watched by an IntersectionObserver; when it enters the
//      viewport we bump `limit` by a page.  The "Load more" button
//      remains as the keyboard / no-IO fallback and as a visible
//      affordance — users shouldn't have to discover that scrolling
//      loads more by chance.
//
//   2. Optimistic posts.  Pending entries from OptimisticPostsContext
//      are rendered above the server posts when there is no active
//      search.  They live through the in-flight POST and disappear
//      shortly after the feed refetches.

import { useEffect, useRef, useState } from "react";
import { usePosts } from "../hooks/usePosts";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useOptimisticPosts } from "../hooks/useOptimisticPosts";
import { useShortcuts } from "../hooks/useShortcuts";
import { PostRow } from "../components/PostRow";
import { PendingPostRow } from "../components/PendingPostRow";
import { Loadable } from "../components/Loadable";
import { Spinner } from "../components/Spinner";
import styles from "./FeedView.module.css";

const PAGE_SIZE = 20;

export function FeedView() {
  const [q, setQ] = useState("");
  const debouncedQ = useDebouncedValue(q, 300);
  const [limit, setLimit] = useState(PAGE_SIZE);

  const state = usePosts({ limit, offset: 0, q: debouncedQ });
  const { pending, retry, dismiss } = useOptimisticPosts();
  const { registerSearchFocus } = useShortcuts();

  const searchRef = useRef<HTMLInputElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Tell the global shortcut layer how to focus our search box, so
  // the "/" key works from anywhere on the feed page.
  useEffect(() => {
    registerSearchFocus(() => searchRef.current?.focus());
    return () => registerSearchFocus(null);
  }, [registerSearchFocus]);

  // Infinite scroll: when the sentinel scrolls into view, request
  // another page.  We only do this if (a) we already have data, (b)
  // we're not currently loading, and (c) the previous fetch returned
  // a full page (which is our "maybe more" heuristic, since A2's
  // GET /posts returns a bare array, no `total`).
  const maybeMore = state.data !== null && state.data.length === limit;
  useEffect(() => {
    if (!sentinelRef.current || !maybeMore || state.loading) return;
    const obs = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) {
        setLimit((n) => n + PAGE_SIZE);
      }
    }, { rootMargin: "200px" });
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [maybeMore, state.loading]);

  // Pending optimistic posts are only sensible when the user isn't
  // searching — they'd never match the query anyway.
  const showOptimistic = debouncedQ.trim() === "";

  return (
    <div className={styles.feed}>
      <header className={styles.header}>
        <h2 className={styles.title}>Feed</h2>
        <label htmlFor="feed-search" className={styles.srOnly}>Search posts</label>
        <input
          id="feed-search"
          ref={searchRef}
          type="search"
          placeholder="Search posts…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setLimit(PAGE_SIZE); // reset pagination on new search
          }}
          className={styles.search}
        />
      </header>

      <Loadable
        state={state}
        emptyMessage={
          showOptimistic && pending.length > 0
            ? "" // suppress empty message when we have pending entries to show
            : debouncedQ
              ? "No posts match that search."
              : "No posts yet. Be the first."
        }
      >
        {(posts) => (
          <>
            <div className={styles.list}>
              {showOptimistic &&
                pending.map((p) => (
                  <PendingPostRow
                    key={p.tempId}
                    post={p}
                    onRetry={() => retry(p.tempId)}
                    onDismiss={() => dismiss(p.tempId)}
                  />
                ))}
              {posts.map((p) => (
                <PostRow key={p.id} post={p} />
              ))}
            </div>
            {maybeMore && (
              <>
                <div ref={sentinelRef} aria-hidden className={styles.sentinel} />
                <div className={styles.loadMoreWrap}>
                  <button
                    type="button"
                    className={styles.loadMore}
                    onClick={() => setLimit((n) => n + PAGE_SIZE)}
                    disabled={state.loading}
                  >
                    {state.loading ? (<><Spinner /> Loading…</>) : "Load more"}
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </Loadable>

      {/* Optimistic-only render: empty server state but we have a pending entry. */}
      {showOptimistic &&
        state.data !== null &&
        state.data.length === 0 &&
        pending.length > 0 && (
          <div className={styles.list}>
            {pending.map((p) => (
              <PendingPostRow
                key={p.tempId}
                post={p}
                onRetry={() => retry(p.tempId)}
                onDismiss={() => dismiss(p.tempId)}
              />
            ))}
          </div>
        )}
    </div>
  );
}
