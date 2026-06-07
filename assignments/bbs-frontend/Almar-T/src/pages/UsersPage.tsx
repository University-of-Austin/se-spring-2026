import { Link } from "react-router-dom";
import { listUsers } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingDots } from "../components/LoadingDots";
import styles from "./UsersPage.module.css";

export default function UsersPage() {
  const { data, error, loading, refetch } = useFetch(() => listUsers(), []);

  if (loading) return <LoadingDots label="Loading users" />;
  if (error) return <ErrorBanner error={error} onRetry={refetch} />;
  const users = data ?? [];

  return (
    <div className={styles.page}>
      <h1>Users</h1>
      {users.length === 0 ? (
        <p className={styles.empty}>No users yet.</p>
      ) : (
        <ul className={styles.list}>
          {users.map((u) => (
            <li key={u.username}>
              <Link to={`/users/${encodeURIComponent(u.username)}`} className={styles.row}>
                <span className={styles.name}>@{u.username}</span>
                <span className={styles.count}>
                  {u.post_count} {u.post_count === 1 ? "post" : "posts"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
