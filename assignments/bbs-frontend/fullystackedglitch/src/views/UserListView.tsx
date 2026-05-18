import { useCallback } from "react";
import { Link } from "react-router-dom";
import {
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
} from "../components/StatusBlock";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import styles from "./UserListView.module.css";

export function UserListView() {
  const fetcher = useCallback((signal: AbortSignal) => api.listUsers(signal), []);
  const { data, loading, error, refetch } = useApi(fetcher, "users");

  return (
    <section>
      <h1>users</h1>
      {loading && <LoadingBlock label="Loading users" />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}
      {data && data.length === 0 && (
        <EmptyBlock>
          no users yet — <Link to="/signup">create one</Link>.
        </EmptyBlock>
      )}
      {data && data.length > 0 && (
        <ul className={styles.list}>
          {data.map((u) => (
            <li key={u.username} className={styles.row}>
              <Link to={`/users/${u.username}`} className={styles.name}>
                @{u.username}
              </Link>
              <span className={styles.meta}>
                {u.post_count} post{u.post_count === 1 ? "" : "s"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
