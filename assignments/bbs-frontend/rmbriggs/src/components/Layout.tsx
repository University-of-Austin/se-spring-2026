import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useTheme } from "@/hooks/useTheme";

export default function Layout() {
  const { username, clearUsername } = useCurrentUser();
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-card">
        <div className="max-w-3xl mx-auto px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="text-lg font-semibold">BBS</Link>
          <nav className="flex gap-3 text-sm text-muted-foreground">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "text-foreground" : "")}>Feed</NavLink>
            <NavLink to="/users" className={({ isActive }) => (isActive ? "text-foreground" : "")}>Users</NavLink>
            <NavLink to="/boards" className={({ isActive }) => (isActive ? "text-foreground" : "")}>Boards</NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <button
              onClick={toggle}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              className="text-base leading-none rounded p-1 hover:bg-accent"
            >
              {theme === "dark" ? "☀" : "☾"}
            </button>
            {username ? (
              <span className="flex items-center gap-2">
                <span className="text-muted-foreground">signed in as</span>
                <span className="font-medium">{username}</span>
                <button
                  className="text-muted-foreground underline"
                  onClick={() => { clearUsername(); navigate("/login"); }}
                >
                  switch
                </button>
              </span>
            ) : (
              <Link to="/login" className="underline">sign in</Link>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-border text-xs text-muted-foreground">
        <div className="max-w-3xl mx-auto px-4 py-2">
          Shortcuts: <kbd className="border px-1 rounded">/</kbd> search · <kbd className="border px-1 rounded">⌘↵</kbd> post
        </div>
      </footer>
    </div>
  );
}
