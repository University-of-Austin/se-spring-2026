import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFeed } from '../hooks/useFeed';
import { useDebounced } from '../hooks/useDebounced';
import { PostCard } from '../components/PostCard';
import { PostForm } from '../components/PostForm';
import { SearchInput } from '../components/SearchInput';
import { Skeleton } from '../components/Skeleton';
import { ErrorBox } from '../components/ErrorBox';
import { RevalidatingBar } from '../components/RevalidatingBar';

export function FeedPage() {
  const [params, setParams] = useSearchParams();
  const initialQ = params.get('q') ?? '';
  const [q, setQ] = useState<string>(initialQ);
  const debouncedQ = useDebounced(q, 300);

  // Sync debounced q to URL so it survives refresh and is shareable.
  useEffect(() => {
    const next = new URLSearchParams(params);
    if (debouncedQ) next.set('q', debouncedQ);
    else next.delete('q');
    setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  const feed = useFeed({ q: debouncedQ });

  return (
    <>
      <RevalidatingBar active={feed.revalidating} />
      <div className="page-header">
        <h1>Feed</h1>
        <span className="page-header__sub">
          {feed.posts.length} loaded · polls every 5s
        </span>
      </div>

      <PostForm onPosted={() => void feed.refetch()} />

      <SearchInput value={q} onChange={setQ} />

      {feed.error && !feed.posts.length && (
        <ErrorBox error={feed.error} onRetry={() => void feed.refetch()} />
      )}

      {feed.loading ? (
        <Skeleton count={4} />
      ) : feed.posts.length === 0 ? (
        <div className="empty-state">
          {debouncedQ ? `No posts match "${debouncedQ}"` : 'No posts yet. Be the first.'}
        </div>
      ) : (
        <>
          {feed.posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onDelete={(id) => void feed.deletePost(id)}
            />
          ))}
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 'var(--space-4)' }}>
            {feed.hasMore ? (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => void feed.loadMore()}
                disabled={feed.loadingMore}
              >
                {feed.loadingMore ? 'Loading...' : 'Load more'}
              </button>
            ) : (
              <span className="page-header__sub">— end of feed —</span>
            )}
          </div>
        </>
      )}
    </>
  );
}
