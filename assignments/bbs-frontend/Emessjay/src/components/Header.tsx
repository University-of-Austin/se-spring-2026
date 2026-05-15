// Persistent top chrome.  NavLink handles active-tab styling: it adds
// aria-current="page" automatically and gives us an `isActive` flag
// to drive the underline.
//
// Identity is surfaced here so the user always sees which name will
// appear on their next post — the X-Username "not real auth" reality
// stays visible.

import { NavLink } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { paths } from "../router/paths";
import styles from "./Header.module.css";

type Tab = { to: string; label: string; end?: boolean };

const tabs: Tab[] = [
  { to: paths.feed(), label: "Feed", end: true },
  { to: paths.compose(), label: "Compose" },
  { to: paths.users(), label: "Users" },
  { to: paths.identity(), label: "Identity" },
];

export function Header() {
  const { username } = useCurrentUser();

  return (
    <header className={styles.header}>
      <div className={styles.brandRow}>
        <h1 className={styles.brand} aria-label="JBBS">
          <span className={styles.brandJ}>J</span>BBS
        </h1>
        <span className={styles.who}>
          {username ? (
            <>posting as <strong className={styles.whoName}>@{username}</strong></>
          ) : (
            <em>not signed in</em>
          )}
        </span>
      </div>
      <nav className={styles.nav} aria-label="Main">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `${styles.tab} ${isActive ? styles.tabActive : ""}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
