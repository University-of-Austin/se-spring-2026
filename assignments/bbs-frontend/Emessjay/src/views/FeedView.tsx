// The feed view.  Owns the search + pagination state; usePosts
// re-runs whenever any of (limit, offset, q) change.
//
// Pagination strategy: "load more".  Because A2 returns a bare array
// and not a {total, next} envelope, we use the heuristic "we got back
// exactly `limit` items, so there might be more".  When the response
// is shorter than `limit`, we hide the Load More button.
//
// Search uses useDebouncedValue so the URL ?q= only fires 300ms
// after the user stops typing, not on every keystroke.

import { useState } from "react";
import { usePosts } from "../hooks/usePosts";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { PostRow } from "../components/PostRow";
import { Loadable } from "../components/Loadable";
import styles from "./FeedView.module.css";

const PAGE_SIZE = 20;

export function FeedView() {
  const [q, setQ] = useState("");
  const debouncedQ = useDebouncedValue(q, 300);
  const [limit, setLimit] = useState(PAGE_SIZE);

  const state = usePosts({ limit, offset: 0, q: debouncedQ });

  // "Maybe more" if the latest fetch returned a full page.
  const maybeMore = state.data !== null && state.data.length === limit;

  return (
    <div className={styles.feed}>
      <header className={styles.header}>
        <h2 className={styles.title}>Feed</h2>
        <input
          type="search"
          aria-label="Search posts"
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
        emptyMessage={debouncedQ ? "No posts match that search." : "No posts yet. Be the first."}
      >
        {(posts) => (
          <>
            <div className={styles.list}>
              {posts.map((p) => (
                <PostRow key={p.id} post={p} />
              ))}
            </div>
            {maybeMore && (
              <div className={styles.loadMoreWrap}>
                <button
                  type="button"
                  className={styles.loadMore}
                  onClick={() => setLimit((n) => n + PAGE_SIZE)}
                  disabled={state.loading}
                >
                  {state.loading ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </>
        )}
      </Loadable>
    </div>
  );
}
