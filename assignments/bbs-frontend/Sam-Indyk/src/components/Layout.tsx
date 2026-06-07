import { type ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useUser } from "../hooks/useUser";

const SHORTCUTS_KEY = "h"; // press '?' or shift+/ to toggle hints panel

export function Layout({ children }: { children: ReactNode }) {
  const { username } = useUser();
  const navigate = useNavigate();
  const [showHints, setShowHints] = useState(false);

  // Global keyboard shortcuts:
  //   g f -> feed,  g u -> users,  g a -> auth,   ? -> hints overlay
  // Cmd/Ctrl+Enter for posting is handled inside the Compose component.
  useEffect(() => {
    let lastKey: { key: string; t: number } | null = null;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const inField =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (inField) return;

      // Shift+/ produces '?' on US layout.
      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        e.preventDefault();
        setShowHints((s) => !s);
        return;
      }

      const now = Date.now();
      if (lastKey && lastKey.key === "g" && now - lastKey.t < 1000) {
        lastKey = null;
        if (e.key === "f") {
          e.preventDefault();
          navigate("/");
        } else if (e.key === "u") {
          e.preventDefault();
          navigate("/users");
        } else if (e.key === "a") {
          e.preventDefault();
          navigate("/auth");
        }
        return;
      }
      if (e.key === "g") {
        lastKey = { key: "g", t: now };
      } else {
        lastKey = null;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    <div className="app">
      <header className="topbar" role="banner">
        <Link to="/" className="topbar-brand" aria-label="Home — Feed">
          BBS
        </Link>
        <nav className="topbar-nav" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Feed
          </NavLink>
          <NavLink to="/users" className={({ isActive }) => (isActive ? "active" : "")}>
            Users
          </NavLink>
          <NavLink to="/auth" className={({ isActive }) => (isActive ? "active" : "")}>
            {username ? "Switch user" : "Sign in"}
          </NavLink>
        </nav>
        <div className="topbar-spacer" />
        <div className="topbar-user" aria-live="polite">
          {username ? (
            <>
              <span className="who">posting as</span>
              <Link to={`/users/${encodeURIComponent(username)}`} className="name">
                {username}
              </Link>
            </>
          ) : (
            <span className="who">not signed in</span>
          )}
        </div>
      </header>

      <main className="main" id="main">
        {children}
      </main>

      <footer className="footer" role="contentinfo">
        BBS — A4 frontend.&nbsp;
        Press <kbd>?</kbd> for shortcuts.&nbsp;
        <span style={{ visibility: "hidden", position: "absolute" }}>{SHORTCUTS_KEY}</span>
      </footer>

      {showHints && (
        <div
          className="toast-row"
          style={{ bottom: "50%" }}
          role="dialog"
          aria-label="Keyboard shortcuts"
        >
          <div className="toast" style={{ pointerEvents: "auto", maxWidth: 360 }}>
            <strong style={{ fontFamily: "var(--font-mono)" }}>Shortcuts</strong>
            <ul style={{ margin: "var(--sp-2) 0 0", paddingLeft: "var(--sp-4)", lineHeight: 1.7 }}>
              <li><kbd>?</kbd> &nbsp; toggle this panel</li>
              <li><kbd>g</kbd> then <kbd>f</kbd> &nbsp; feed</li>
              <li><kbd>g</kbd> then <kbd>u</kbd> &nbsp; users</li>
              <li><kbd>g</kbd> then <kbd>a</kbd> &nbsp; sign-in</li>
              <li><kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>Enter</kbd> &nbsp; post message</li>
            </ul>
            <button
              type="button"
              className="btn btn-ghost"
              style={{ marginTop: "var(--sp-3)" }}
              onClick={() => setShowHints(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
