import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { setStoredUsername } from "../lib/storage";
import { ShortcutOverlay } from "./ShortcutOverlay";
import styles from "./Layout.module.css";

export function Layout() {
  const username = useCurrentUser();
  const navigate = useNavigate();

  const signOut = () => {
    setStoredUsername(null);
    navigate("/signup");
  };

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <Link to="/" className={styles.brandTitle}>
            bbs
          </Link>
          <nav className={styles.nav} aria-label="Primary">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? `${styles.navLink} ${styles.navLinkActive}`
                  : styles.navLink
              }
            >
              feed
            </NavLink>
            <NavLink
              to="/users"
              className={({ isActive }) =>
                isActive
                  ? `${styles.navLink} ${styles.navLinkActive}`
                  : styles.navLink
              }
            >
              users
            </NavLink>
          </nav>
        </div>
        <div className={styles.identity}>
          {username ? (
            <>
              <span>
                signed in as{" "}
                <Link to={`/users/${username}`} className={styles.identityName}>
                  @{username}
                </Link>
              </span>
              <button
                type="button"
                onClick={signOut}
                className={styles.linkButton}
              >
                switch user
              </button>
            </>
          ) : (
            <Link to="/signup">sign in</Link>
          )}
        </div>
      </header>

      <main>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <span>BBS frontend — A4</span>
        <span>
          press <kbd>?</kbd> for shortcuts
        </span>
      </footer>

      <ShortcutOverlay />
    </div>
  );
}
