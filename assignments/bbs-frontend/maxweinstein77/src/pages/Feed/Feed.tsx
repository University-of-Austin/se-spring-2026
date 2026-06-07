// Feed page (Substack-style layout):
//   - Inline compose box at the top ("What's on your mind, alice?")
//   - Search box
//   - Feed list, infinite-scrolls when you reach the bottom
//   - Gold pick #1: 3s polling + "N new posts" banner

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ComposeForm } from "../../components/ComposeForm";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { NewPostsBanner } from "../../components/NewPostsBanner";
import { PostRow } from "../../components/PostRow";
import { useDebouncedValue } from "../../lib/useDebouncedValue";
import { errorText } from "../../lib/errorText";
import { useDeletePost, useFeed, useLatestPosts } from "../../hooks/usePosts";
import styles from "./Feed.module.css";

export function Feed() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const feed = useFeed(debouncedSearch);
  const latest = useLatestPosts(debouncedSearch);
  const deletePost = useDeletePost();

  const posts = feed.data?.pages.flat() ?? [];

  // Infinite-scroll sentinel: when this div enters the viewport, fetch the
  // next page. IntersectionObserver instead of scroll listener (less work,
  // no manual scroll math). Destructured to keep deps stable -- React Query
  // re-creates `feed` itself every render, but the inner values are stable.
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = feed;
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { rootMargin: "200px" }, // pre-fetch a bit before the bottom
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Banner: count posts in the polled "latest" that aren't visible yet.
  // Negative ids are optimistic temp posts; ignore them when deciding
  // what counts as "new" to avoid a user's own post triggering the banner.
  const newCount = useMemo(() => {
    const visibleIds = new Set(posts.map((p) => p.id));
    const maxVisibleId = posts.reduce((max, p) => (p.id > max ? p.id : max), 0);
    return (latest.data ?? []).filter(
      (p) => p.id > maxVisibleId && !visibleIds.has(p.id),
    ).length;
  }, [posts, latest.data]);

  function handleBannerClick() {
    feed.refetch();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <section className={styles.wrap}>
      <ComposeForm inline />

      <header className={styles.header}>
        <h1 className={styles.title}>Feed</h1>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search posts"
          aria-label="Search posts"
          className={styles.search}
        />
      </header>

      <NewPostsBanner count={newCount} onClick={handleBannerClick} />

      {feed.isLoading && <Loading label="Loading posts..." />}

      {feed.isError && (
        <ErrorMessage
          message={errorText(feed.error, "Failed to load feed.")}
          onRetry={() => feed.refetch()}
        />
      )}

      {feed.isSuccess && posts.length === 0 && (
        <div className={styles.empty}>
          {debouncedSearch
            ? <>No posts match "{debouncedSearch}".</>
            : <>No posts yet. <Link to="/compose">Be the first</Link>.</>}
        </div>
      )}

      {posts.length > 0 && (
        <ul className={styles.list}>
          {posts.map((post) => (
            <li key={post.id}>
              <PostRow
                post={post}
                onDelete={(id) => deletePost.mutate(id)}
                deleting={deletePost.isPending && deletePost.variables === post.id}
              />
            </li>
          ))}
        </ul>
      )}

      {/* Infinite-scroll sentinel + spinner */}
      {feed.hasNextPage && (
        <div ref={sentinelRef} className={styles.sentinel}>
          {feed.isFetchingNextPage ? <Loading label="Loading more..." /> : null}
        </div>
      )}

      {!feed.hasNextPage && posts.length > 0 && (
        <p className={styles.endNote}>You've reached the end.</p>
      )}
    </section>
  );
}
