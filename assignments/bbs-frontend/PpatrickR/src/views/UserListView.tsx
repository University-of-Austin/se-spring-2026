import { useCallback } from "react";
import { Link } from "react-router-dom";
import { listUsers } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { Loading, ErrorBlock } from "../components/StatusBlock";

export function UserListView() {
  const fetcher = useCallback(() => listUsers(), []);
  const { data, error, loading, reload } = useFetch(fetcher, []);

  return (
    <section className="view users-view">
      <h1>Users</h1>

      {loading && <Loading />}
      {error && <ErrorBlock error={error} onRetry={reload} />}

      {!loading && !error && data && (
        <>
          {data.length === 0 ? (
            <div className="empty">No users yet.</div>
          ) : (
            <ul className="user-list">
              {data.map((u) => (
                <li key={u.username}>
                  <Link
                    to={`/users/${encodeURIComponent(u.username)}`}
                    className="user-row"
                  >
                    <span className="user-name">@{u.username}</span>
                    <span className="muted small">
                      {u.post_count} post{u.post_count === 1 ? "" : "s"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
