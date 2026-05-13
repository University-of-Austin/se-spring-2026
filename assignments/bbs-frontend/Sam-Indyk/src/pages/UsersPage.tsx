import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import { useApi } from "../hooks/useApi";

export function UsersPage() {
  const { data, loading, error, refetch } = useApi(
    (signal) => api.listUsers(signal),
    []
  );

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Users</h1>
          <div className="sub">Everyone who has signed up.</div>
        </div>
        <Link to="/auth" className="btn">
          Create user
        </Link>
      </div>

      {error && <ErrorBanner error={error} onRetry={refetch} />}
      {loading && !data && <Spinner label="Loading users" />}

      {data && data.length === 0 && (
        <EmptyState
          title="No users yet"
          description="Create the first account."
          action={
            <Link to="/auth" className="btn btn-primary">
              Create user
            </Link>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="user-list">
          {data.map((u) => (
            <Link
              key={u.username}
              to={`/users/${encodeURIComponent(u.username)}`}
              className="user-card"
            >
              <span>{u.username}</span>
              <span className="count">
                {u.post_count} {u.post_count === 1 ? "post" : "posts"}
              </span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
