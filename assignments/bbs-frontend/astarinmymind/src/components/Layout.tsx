// The shell that wraps every page.
// Routes are configured in App.tsx so this Layout sits around all of them,
// meaning the header + footer hint show on every URL.
//
// Owns the global keyboard shortcut state for `?` (open overlay) and Escape
// (close overlay). The `/` (focus search) shortcut lives in FeedPage since
// it's page-specific.

import { useState, useEffect } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useCurrentUser } from '../context/UserContext'
import { ShortcutOverlay } from './ShortcutOverlay'

// Shortcuts shouldn't fire while the user is typing in a form field.
function isTypingInInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.isContentEditable
  )
}

export function Layout() {
  const { username, setUsername } = useCurrentUser()
  const navigate = useNavigate()
  const [overlayOpen, setOverlayOpen] = useState(false)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Always allow Escape to close the overlay, even from inside form fields.
      if (e.key === 'Escape' && overlayOpen) {
        setOverlayOpen(false)
        return
      }
      // Don't hijack `?` while typing.
      if (isTypingInInput(e.target)) return
      if (e.key === '?') {
        e.preventDefault()
        setOverlayOpen(o => !o)
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [overlayOpen])

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

      <footer className="border-t border-border py-3">
        <div className="max-w-2xl mx-auto px-4 text-xs text-muted">
          Press <kbd className="font-mono">?</kbd> for shortcuts
        </div>
      </footer>

      <ShortcutOverlay open={overlayOpen} onClose={() => setOverlayOpen(false)} />
    </div>
  )
}
