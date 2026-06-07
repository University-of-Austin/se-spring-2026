import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useDarkMode } from "../hooks/useDarkMode";
import { KeyboardHelp } from "./KeyboardHelp";

export const FOCUS_SEARCH_EVENT = "bbs:focus-search";

export function Layout() {
  const { username, signOut } = useAuth();
  const { theme, toggle } = useDarkMode();
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link to="/" className="brand" aria-label="BBS home">
            <span className="brand-mark">▮▮</span>
            <span className="brand-name">BBS</span>
          </Link>
          <nav className="nav-tabs" aria-label="Primary">
            <NavLink to="/" end>
              Feed
            </NavLink>
            <NavLink to="/users">Users</NavLink>
            <NavLink to="/signup">{username ? "Switch" : "Sign in"}</NavLink>
          </nav>
          <div className="header-right">
            <button
              type="button"
              className="theme-toggle"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              onClick={toggle}
            >
              {theme === "dark" ? "☀" : "☾"}
            </button>
            {username ? (
              <div className="who">
                as <Link to={`/users/${encodeURIComponent(username)}`}>@{username}</Link>
                <button type="button" className="btn btn-ghost btn-sm" onClick={signOut}>
                  Sign out
                </button>
              </div>
            ) : (
              <Link to="/signup" className="btn btn-primary btn-sm">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>Press <kbd>?</kbd> for keyboard shortcuts</span>
      </footer>
      <KeyboardHelp
        onNavigate={(p) => navigate(p)}
        onToggleTheme={toggle}
        onFocusSearch={() => window.dispatchEvent(new CustomEvent(FOCUS_SEARCH_EVENT))}
      />
    </div>
  );
}
