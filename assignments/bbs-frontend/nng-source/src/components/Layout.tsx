import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../api";
import { Avatar } from "./Avatar";
import { ComposeModal } from "./ComposeModal";

const UNREAD_POLL_MS = 30000;

export function Layout() {
  const { username, token, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [myAvatar, setMyAvatar] = useState<string | null>(null);
  const [unreadDMs, setUnreadDMs] = useState(0);
  const [composeOpen, setComposeOpen] = useState(false);

  // Board from the URL, if any -- so the FAB posts into the active board.
  const activeBoard = location.pathname === "/" ? (searchParams.get("board") ?? "") : "";

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

  // Poll for total unread DM count to show a badge on the nav link. Refresh
  // immediately on route change so opening a thread clears the badge fast.
  useEffect(() => {
    if (!token) { setUnreadDMs(0); return; }
    let cancelled = false;
    async function poll() {
      try {
        const convos = await api.listDMs(token!);
        if (!cancelled) {
          setUnreadDMs(convos.reduce((s, c) => s + c.unread_count, 0));
        }
      } catch { /* ignore */ }
    }
    void poll();
    const id = setInterval(() => { if (!document.hidden) void poll(); }, UNREAD_POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [token, location.pathname]);

  // Global keyboard shortcuts:
  //   "/"  -> focus search box on feed
  //   "n"  -> open the compose modal (Cmd+Enter inside it submits)
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
        if (!username) return;
        e.preventDefault();
        setComposeOpen(true);
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [username]);

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
            {username && (
              <NavLink to="/dms" className="nav-with-badge">
                DMs
                {unreadDMs > 0 && (
                  <span className="nav-badge" aria-label={`${unreadDMs} unread`}>
                    {unreadDMs}
                  </span>
                )}
              </NavLink>
            )}
          </nav>
          <div className="auth-status">
            {username ? (
              <>
                <Link to={`/users/${encodeURIComponent(username)}`} className="auth-username">
                  <Avatar username={username} src={myAvatar} size="sm" />
                  <span>{username}</span>
                </Link>
                <Link to="/settings" className="btn btn-link btn-sm" aria-label="Settings">
                  ⚙
                </Link>
                <button type="button" onClick={onLogout} className="btn btn-link btn-sm">
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

      {username && (
        <button
          type="button"
          className="compose-fab"
          onClick={() => setComposeOpen(true)}
          aria-label="New post"
          title="New post (n)"
        >
          <span aria-hidden="true">+</span>
        </button>
      )}
      {composeOpen && username && (
        <ComposeModal
          board={activeBoard || undefined}
          onClose={() => setComposeOpen(false)}
        />
      )}
    </div>
  );
}
