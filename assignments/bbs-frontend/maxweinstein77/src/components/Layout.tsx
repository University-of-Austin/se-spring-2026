// Page shell: minimal Substack-style header + Discord-style left user
// sidebar (always visible on desktop, hidden on mobile). Composing happens
// inline at the top of the Feed. First-time visitors landing on "/"
// without a stored username are auto-redirected to /signin.

import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useUsername } from "../hooks/useUsername";
import { ShortcutsOverlay } from "./ShortcutsOverlay";
import { UserSidebar } from "./UserSidebar";
import styles from "./Layout.module.css";

export function Layout() {
  const { username, clearUsername } = useUsername();
  const navigate = useNavigate();
  const location = useLocation();
  const [helpOpen, setHelpOpen] = useState(false);

  // Auto-redirect first-time visitors to the SignIn screen.
  useEffect(() => {
    if (!username && location.pathname === "/") {
      navigate("/signin", { replace: true });
    }
  }, [username, location.pathname, navigate]);

  // Global "?" key opens shortcuts; Esc closes.
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable;
      if (e.key === "?" && !typing) {
        e.preventDefault();
        setHelpOpen((v) => !v);
      } else if (e.key === "Escape") {
        setHelpOpen(false);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  function handleSwitch() {
    clearUsername();
    navigate("/signin");
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <Link to="/" className={styles.brand}>
          <span className={styles.brandIcon} aria-hidden="true">📮</span>
          Postack
        </Link>
        <div className={styles.right}>
          {username ? (
            <>
              <span className={styles.identity}>
                Hello, <strong>{username}</strong>
              </span>
              <button type="button" onClick={handleSwitch} className={styles.switchBtn}>
                Sign out
              </button>
            </>
          ) : (
            <Link to="/signin" className={styles.signInLink}>Sign in</Link>
          )}
        </div>
      </header>
      <div className={styles.body}>
        <main className={styles.main}>
          <Outlet />
        </main>
        <UserSidebar />
      </div>
      <button
        type="button"
        onClick={() => setHelpOpen(true)}
        className={styles.helpFab}
        aria-label="Show keyboard shortcuts"
        title="Keyboard shortcuts (?)"
      >
        ?
      </button>
      <ShortcutsOverlay open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
