import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '../hooks/useQuery';
import { usePolling } from '../hooks/usePolling';
import { api } from '../api/endpoints';
import { PostCard } from '../components/PostCard';
import { Skeleton } from '../components/Skeleton';
import { ErrorBox } from '../components/ErrorBox';
import { RevalidatingBar } from '../components/RevalidatingBar';

export function UserProfilePage() {
  const { username = '' } = useParams<{ username: string }>();

  const userFetcher = useCallback(
    (signal: AbortSignal) => api.getUser(username, { signal }),
    [username],
  );
  const userQuery = useQuery(userFetcher, [username]);

  const postsFetcher = useCallback(
    (signal: AbortSignal) => api.getUserPosts(username, { signal }),
    [username],
  );
  const postsQuery = useQuery(postsFetcher, [username]);

  // Poll the user's posts list — same 5s freshness story as the feed.
  usePolling(postsQuery.refetch, {
    ms: 5000,
    enabled: postsQuery.data !== undefined,
  });

  // Resource-not-found inside a valid route shape — distinct from the global 404.
  if (userQuery.error?.status === 404) {
    return (
      <>
        <div className="page-header"><h1>User not found</h1></div>
        <div className="empty-state">
          No user named "@{username}".
          <div style={{ marginTop: 'var(--space-3)' }}>
            <Link to="/users" className="btn btn--ghost btn--sm">Browse users</Link>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <RevalidatingBar active={postsQuery.revalidating} />
      <div className="page-header">
        <h1>@{username}</h1>
        {userQuery.data && (
          <span className="page-header__sub">
            {userQuery.data.post_count} posts · joined {new Date(userQuery.data.created_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {userQuery.data?.bio && (
        <p style={{ color: 'var(--fg-muted)', marginBottom: 'var(--space-4)' }}>
          {userQuery.data.bio}
        </p>
      )}

      {userQuery.loading && <Skeleton count={1} />}
      {userQuery.error && userQuery.error.status !== 404 && (
        <ErrorBox error={userQuery.error} onRetry={() => void userQuery.refetch()} />
      )}

      <h2 style={{ margin: 'var(--space-6) 0 var(--space-3)' }}>Posts</h2>
      {postsQuery.loading && <Skeleton count={3} />}
      {postsQuery.error && (
        <ErrorBox error={postsQuery.error} onRetry={() => void postsQuery.refetch()} />
      )}
      {postsQuery.data && postsQuery.data.length === 0 && (
        <div className="empty-state">No posts yet.</div>
      )}
      {postsQuery.data?.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
    </>
  );
}
