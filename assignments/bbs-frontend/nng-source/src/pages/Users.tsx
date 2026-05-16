import { Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";

export function Users() {
  const { data, loading, error, reload } = useAsync(() => api.listUsers(), []);

  return (
    <div className="page page-users">
      <h1>Users</h1>
      {loading && <Spinner label="Loading users..." />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <p className="empty-state">No users yet.</p>}
      {data && data.length > 0 && (
        <ul className="user-list" aria-label="Users">
          {data.map((u) => (
            <li key={u.username} className="user-list-item">
              <Link to={`/users/${encodeURIComponent(u.username)}`}>
                <span className="user-list-name">{u.username}</span>
              </Link>
              <span className="user-list-meta">{u.post_count} posts</span>
              {u.bio && <p className="user-list-bio">{u.bio}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
