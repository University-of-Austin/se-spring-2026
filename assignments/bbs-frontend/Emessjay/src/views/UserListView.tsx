import { useUsers } from "../hooks/useUsers";
import { useRouter } from "../router/useRouter";
import { Loadable } from "../components/Loadable";
import styles from "./UserListView.module.css";

export function UserListView() {
  const state = useUsers();
  const { navigate } = useRouter();

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Users</h2>
      <Loadable state={state} emptyMessage="No users yet.">
        {(users) => (
          <ul className={styles.list}>
            {users.map((u) => (
              <li key={u.username} className={styles.item}>
                <button
                  type="button"
                  className={styles.row}
                  onClick={() => navigate({ view: "user", username: u.username })}
                >
                  <span className={styles.name}>@{u.username}</span>
                  <span className={styles.count}>
                    {u.post_count} {u.post_count === 1 ? "post" : "posts"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Loadable>
    </div>
  );
}
