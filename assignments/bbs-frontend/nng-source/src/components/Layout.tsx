import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../api";
import { Avatar } from "./Avatar";

export function Layout() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const [myAvatar, setMyAvatar] = useState<string | null>(null);

  // Fetch current user's avatar so the header chip shows it. Re-runs whenever
  // the logged-in username changes (login / logout / switch user).
  useEffect(() => {
    if (!username) { setMyAvatar(null); return; }
    let cancelled = false;
    api.getUser(username)
      .then((u) => { if (!cancelled) setMyAvatar(u.avatar_url); })
      .catch(() => { /* ignore -- fallback initial renders fine */ });
    return () => { cancelled = true; };
  }, [username]);

  // Listen for avatar-change events from Profile so the header updates
  // without waiting for a navigation.
  useEffect(() => {
    function onAvatarChange(e: Event) {
      const detail = (e as CustomEvent<{ avatar_url: string | null }>).detail;
      setMyAvatar(detail?.avatar_url ?? null);
    }
    window.addEventListener("bbs:avatar-changed", onAvatarChange);
    return () => window.removeEventListener("bbs:avatar-changed", onAvatarChange);
  }, []);

  // Global keyboard shortcuts:
  //   "/"  -> focus search box on feed
  //   "n"  -> focus compose textarea (Cmd+Enter to submit handled in Compose)
  //   "?"  -> open shortcuts dialog (footer link)
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Ignore when typing in a form field.
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        const search = document.getElementById("feed-search") as HTMLInputElement | null;
        search?.focus();
      } else if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("bbs:focus-compose"));
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link to="/" className="brand">
            <span className="brand-bracket">[</span>
            <span className="brand-name">bbs</span>
            <span className="brand-bracket">]</span>
          </Link>
          <nav className="primary-nav" aria-label="Primary">
            <NavLink to="/" end>Feed</NavLink>
            <NavLink to="/boards">Boards</NavLink>
            <NavLink to="/users">Users</NavLink>
          </nav>
          <div className="auth-status">
            {username ? (
              <>
                <Link to={`/users/${encodeURIComponent(username)}`} className="auth-username">
                  <Avatar username={username} src={myAvatar} size="sm" />
                  <span>{username}</span>
                </Link>
                <button type="button" onClick={onLogout} className="btn btn-link">
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn-link">Log in</Link>
                <Link to="/signup" className="btn btn-primary btn-sm">Sign up</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>Shortcuts: <kbd>/</kbd> search · <kbd>n</kbd> compose · <kbd>Ctrl/Cmd</kbd>+<kbd>Enter</kbd> post</span>
      </footer>
    </div>
  );
}
