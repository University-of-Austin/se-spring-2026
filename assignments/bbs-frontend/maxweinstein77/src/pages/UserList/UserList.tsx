// Standalone /users page. Mostly redundant on desktop (sidebar covers it)
// but kept so the URL is bookmarkable (silver requirement) and so mobile
// users (sidebar hidden < 768px) still have a way to see every user.

import { Link } from "react-router-dom";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { useUsers } from "../../hooks/useUsers";
import { avatarColor } from "../../lib/avatar";
import { errorText } from "../../lib/errorText";
import styles from "./UserList.module.css";

export function UserList() {
  const users = useUsers();

  if (users.isLoading) return <Loading label="Loading users..." />;
  if (users.isError) {
    return (
      <ErrorMessage
        message={errorText(users.error, "Failed to load users.")}
        onRetry={() => users.refetch()}
      />
    );
  }

  const list = users.data ?? [];

  return (
    <section>
      <h1 className={styles.title}>Users</h1>
      {list.length === 0 ? (
        <p className={styles.empty}>No users yet.</p>
      ) : (
        <ul className={styles.list}>
          {list.map((u) => (
            <li key={u.username}>
              <Link to={`/users/${u.username}`} className={styles.row}>
                <span
                  className={styles.avatar}
                  style={{ background: avatarColor(u.username) }}
                  aria-hidden="true"
                >
                  {u.username[0].toUpperCase()}
                </span>
                <span className={styles.username}>{u.username}</span>
                <span className={styles.count}>
                  {u.post_count} {u.post_count === 1 ? "post" : "posts"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
