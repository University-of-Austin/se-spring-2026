// Discord-style left sidebar listing every user, always visible on desktop.
// Hidden on mobile (the standalone /users route covers narrow viewports).
// Each row has a colored avatar circle (deterministic per username) plus
// the name; clicking navigates to that user's profile.

import { NavLink } from "react-router-dom";
import { useUsername } from "../hooks/useUsername";
import { useUsers } from "../hooks/useUsers";
import { avatarColor, avatarInitial } from "../lib/avatar";
import styles from "./UserSidebar.module.css";

export function UserSidebar() {
  const users = useUsers();
  const { username: me } = useUsername();

  return (
    <aside className={styles.sidebar} aria-label="Users">
      <header className={styles.header}>
        <h2 className={styles.heading}>
          Users{users.data ? ` — ${users.data.length}` : ""}
        </h2>
      </header>
      <div className={styles.scroll}>
        {users.isLoading && <p className={styles.note}>Loading...</p>}
        {users.isError && <p className={styles.note}>Failed to load users.</p>}
        {users.data && users.data.length === 0 && (
          <p className={styles.note}>No users yet.</p>
        )}
        {users.data && users.data.length > 0 && (
          <ul className={styles.list}>
            {users.data.map((u) => {
              const isMe = u.username === me;
              return (
                <li key={u.username}>
                  <NavLink
                    to={`/users/${u.username}`}
                    className={({ isActive }) =>
                      `${styles.row} ${isActive ? styles.active : ""}`
                    }
                    title={u.username}
                  >
                    <span
                      className={styles.avatar}
                      style={{ background: avatarColor(u.username) }}
                      aria-hidden="true"
                    >
                      {avatarInitial(u.username)}
                    </span>
                    <span className={styles.name}>
                      {u.username}
                      {isMe && <span className={styles.meTag}>you</span>}
                    </span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
