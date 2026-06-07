import { Link } from "react-router-dom";
import { useCallback } from "react";
import { listUsers } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";

export function UserListPage() {
  const fetcher = useCallback((signal: AbortSignal) => listUsers(signal), []);
  const { data, loading, error, refetch } = useFetch(fetcher, []);

  return (
    <div className="page">
      <h1>Users</h1>
      {loading && <Spinner />}
      {error && <ErrorBanner message={error} onRetry={refetch} />}
      {data && data.length === 0 && <p className="empty-state">No users yet.</p>}
      {data && data.length > 0 && (
        <ul className="user-list">
          {data.map((u) => (
            <li key={u.username} className="user-row">
              <Link to={`/users/${encodeURIComponent(u.username)}`} className="user-row-name">
                @{u.username}
              </Link>
              <span className="user-row-meta">
                {u.post_count} post{u.post_count === 1 ? "" : "s"}
              </span>
              {u.bio && <span className="user-row-bio">{u.bio}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
