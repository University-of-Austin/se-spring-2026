import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export default function Layout() {
  const { username, clearUsername } = useCurrentUser();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-neutral-200 bg-white">
        <div className="max-w-3xl mx-auto px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="text-lg font-semibold">BBS</Link>
          <nav className="flex gap-3 text-sm text-neutral-600">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Feed</NavLink>
            <NavLink to="/users" className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Users</NavLink>
            <NavLink to="/boards" className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Boards</NavLink>
          </nav>
          <div className="ml-auto text-sm">
            {username ? (
              <span className="flex items-center gap-2">
                <span className="text-neutral-500">signed in as</span>
                <span className="font-medium">{username}</span>
                <button
                  className="text-neutral-500 underline"
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
      <footer className="border-t border-neutral-200 text-xs text-neutral-500">
        <div className="max-w-3xl mx-auto px-4 py-2">
          Shortcuts: <kbd className="border px-1 rounded">/</kbd> search · <kbd className="border px-1 rounded">⌘↵</kbd> post
        </div>
      </footer>
    </div>
  );
}
