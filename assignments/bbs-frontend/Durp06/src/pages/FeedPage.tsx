import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFeed } from '../hooks/useFeed';
import { useToast } from '../hooks/useToast';
import { deletePost, ApiError } from '../api/bbs';
import type { Post } from '../api/types';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { PostCard } from '../components/PostCard';

export default function FeedPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQ = searchParams.get('q') ?? '';
  const [searchInput, setSearchInput] = useState(initialQ);
  const [appliedQ, setAppliedQ] = useState(initialQ);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const { push: pushToast } = useToast();

  const feed = useFeed({ q: appliedQ || undefined });

  // Debounce search input → applied query so we don't refetch on every keystroke.
  useEffect(() => {
    const id = window.setTimeout(() => {
      setAppliedQ(searchInput);
      if (searchInput) setSearchParams({ q: searchInput }, { replace: true });
      else setSearchParams({}, { replace: true });
    }, 250);
    return () => window.clearTimeout(id);
    // setSearchParams identity is stable enough for our use
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const handleDelete = useCallback(
    async (post: Post) => {
      const index = feed.posts.findIndex((p) => p.id === post.id);
      setDeletingId(post.id);
      // Mark BEFORE removing — if a poll races us, it shouldn't bring this id back.
      feed.markPendingDelete(post.id);
      feed.removeById(post.id);
      try {
        await deletePost(post.id);
      } catch (err) {
        feed.restore(post, index);
        const msg = err instanceof ApiError ? err.message : (err as Error).message;
        pushToast(`Couldn't delete post: ${msg}`, 'error');
      } finally {
        // Clear in both success and failure — on failure the row is back, and
        // on success the server's view no longer has it anyway.
        feed.clearPendingDelete(post.id);
        setDeletingId(null);
      }
    },
    [feed, pushToast],
  );

  return (
    <section className="page page--feed">
      <header className="page__head">
        <h1>Feed</h1>
        <label className="search">
          <span className="visually-hidden">Search posts</span>
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search posts…"
            aria-label="Search posts"
          />
        </label>
      </header>

      {feed.loading && feed.posts.length === 0 && <Loading label="Loading feed" />}
      {feed.error && feed.posts.length === 0 && (
        <ErrorMessage message={feed.error} onRetry={() => void feed.refetch()} />
      )}

      {feed.posts.length > 0 && (
        <ul className="post-list" aria-label="Posts">
          {feed.posts.map((post) => (
            <li key={post.id} className="post-list__item">
              <PostCard post={post} onDelete={handleDelete} deleting={deletingId === post.id} />
            </li>
          ))}
        </ul>
      )}

      {!feed.loading && !feed.error && feed.posts.length === 0 && (
        <p className="empty">No posts yet. Be the first to post.</p>
      )}

      {feed.nextOffset !== null && (
        <div className="load-more">
          <button
            type="button"
            className="btn"
            onClick={() => void feed.loadMore()}
            disabled={feed.loadingMore}
          >
            {feed.loadingMore ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </section>
  );
}
