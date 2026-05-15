import { Link } from "react-router-dom";
import { useUsers } from "../hooks/useUsers";
import { Loadable } from "../components/Loadable";
import { paths } from "../router/paths";
import styles from "./UserListView.module.css";

export function UserListView() {
  const state = useUsers();

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Users</h2>
      <Loadable state={state} emptyMessage="No users yet.">
        {(users) => (
          <ul className={styles.list}>
            {users.map((u) => (
              <li key={u.username} className={styles.item}>
                <Link to={paths.user(u.username)} className={styles.row}>
                  <span className={styles.name}>@{u.username}</span>
                  <span className={styles.count}>
                    {u.post_count} {u.post_count === 1 ? "post" : "posts"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Loadable>
    </div>
  );
}
