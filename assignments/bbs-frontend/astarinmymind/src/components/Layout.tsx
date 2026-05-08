// The shell that wraps every page.
// Routes are configured in App.tsx so this Layout sits around all of them,
// meaning the header + outer container show on every URL.

import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useCurrentUser } from '../context/UserContext'

export function Layout() {
  const { username, setUsername } = useCurrentUser()
  const navigate = useNavigate()

  const handleSignOut = () => {
    setUsername(null)
    navigate('/signin')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="font-serif text-2xl text-text hover:text-accent">
            BBS
          </Link>

          <nav className="flex items-center gap-4 text-sm">
            <Link to="/users" className="text-muted hover:text-text">
              Users
            </Link>

            {/* Theme toggle placeholder — wired in Phase 5 */}
            <span className="text-muted/40 cursor-not-allowed" aria-hidden>
              🌗
            </span>

            {username ? (
              <>
                <span className="text-muted">@{username}</span>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="text-muted hover:text-text"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link to="/signin" className="text-accent hover:underline">
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full">
        <Outlet />
      </main>
    </div>
  )
}
