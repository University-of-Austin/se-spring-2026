import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '../hooks/useQuery';
import { api } from '../api/endpoints';
import { Skeleton } from '../components/Skeleton';
import { ErrorBox } from '../components/ErrorBox';

export function UserListPage() {
  const fetcher = useCallback(
    (signal: AbortSignal) => api.listUsers({ signal }),
    [],
  );
  const { data, loading, error, refetch } = useQuery(fetcher, []);

  return (
    <>
      <div className="page-header">
        <h1>Users</h1>
        <span className="page-header__sub">
          {data ? `${data.length} total` : ''}
        </span>
      </div>

      {error && !data && <ErrorBox error={error} onRetry={() => void refetch()} />}
      {loading && <Skeleton count={5} />}
      {data && data.length === 0 && (
        <div className="empty-state">No users yet.</div>
      )}
      {data && data.length > 0 && (
        <ul className="user-list">
          {data.map((u) => (
            <li key={u.username}>
              <Link to={`/users/${encodeURIComponent(u.username)}`}>
                @{u.username}
                <span className="user-list__count">
                  {u.post_count} {u.post_count === 1 ? 'post' : 'posts'}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
