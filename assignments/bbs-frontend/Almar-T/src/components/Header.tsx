import { NavLink, useNavigate } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useTheme } from "../hooks/useTheme";
import styles from "./Header.module.css";

export function Header({ onOpenHelp }: { onOpenHelp: () => void }) {
  const { currentUser, setCurrentUser } = useCurrentUser();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const onSignOut = () => {
    setCurrentUser(null);
    navigate("/sign-in");
  };

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.brand} aria-label="BBS home">
          <span className={styles.brandMark}>▌</span>
          <span className={styles.brandName}>BBS</span>
        </NavLink>

        <nav className={styles.nav} aria-label="Primary">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive ? `${styles.link} ${styles.linkActive}` : styles.link
            }
          >
            Feed
          </NavLink>
          <NavLink
            to="/users"
            className={({ isActive }) =>
              isActive ? `${styles.link} ${styles.linkActive}` : styles.link
            }
          >
            Users
          </NavLink>
        </nav>

        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onOpenHelp}
            aria-label="Show keyboard shortcuts"
            title="Keyboard shortcuts (?)"
          >
            ?
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            title={`Theme: ${theme}`}
          >
            {theme === "dark" ? "☾" : "☀"}
          </button>
          {currentUser ? (
            <div className={styles.userGroup}>
              <NavLink
                to={`/users/${encodeURIComponent(currentUser)}`}
                className={styles.userChip}
                aria-label={`Your profile: ${currentUser}`}
              >
                @{currentUser}
              </NavLink>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={onSignOut}
              >
                Switch
              </button>
            </div>
          ) : (
            <NavLink to="/sign-in" className="btn btn-primary">
              Sign in
            </NavLink>
          )}
        </div>
      </div>
    </header>
  );
}
