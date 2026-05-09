// The shell that wraps every page.
// Routes are configured in App.tsx so this Layout sits around all of them,
// meaning the header + footer hint show on every URL.
//
// Owns the global keyboard shortcut state for `?` (open overlay) and Escape
// (close overlay). The `/` (focus search) shortcut lives in FeedPage since
// it's page-specific.

import { useState, useEffect } from 'react'
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useCurrentUser } from '../context/useCurrentUser'
import { ShortcutOverlay } from './ShortcutOverlay'
import { ThemeToggle } from './ThemeToggle'

// Shortcuts shouldn't fire while the user is typing in a form field.
function isTypingInInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.isContentEditable
  )
}

// Kepano-style breadcrumb suffix shown after "BBS" in the header.
// Returns null on the home page (no slash, just "BBS").
function getCrumb(pathname: string): string | null {
  if (pathname === '/users') return 'Users'
  if (pathname.startsWith('/users/')) {
    const name = pathname.slice('/users/'.length)
    return name ? `@${name}` : 'Users'
  }
  if (pathname.startsWith('/posts/')) {
    const id = pathname.slice('/posts/'.length)
    return id ? `Post #${id}` : 'Post'
  }
  if (pathname === '/signin') return 'Sign in'
  return null
}

export function Layout() {
  const { username, setUsername } = useCurrentUser()
  const navigate = useNavigate()
  const location = useLocation()
  const crumb = getCrumb(location.pathname)
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
      <header>
        <div className="max-w-2xl mx-auto px-4 pt-12 pb-4 flex items-center justify-between">
          <div className="flex items-baseline gap-2 font-serif text-xl">
            <Link to="/" className="text-text hover:text-accent transition-colors">
              BBS
            </Link>
            {crumb && (
              <>
                <span className="text-muted">/</span>
                <span className="text-muted">{crumb}</span>
              </>
            )}
          </div>

          <nav className="flex items-center gap-6 text-base">
            <Link to="/users" className="text-muted hover:text-accent transition-colors">
              Users
            </Link>

            <ThemeToggle />

            {username ? (
              <span className="flex items-center gap-3 border-l border-border pl-6">
                <Link
                  to={`/users/${username}`}
                  className="text-accent hover:opacity-80 transition-opacity"
                >
                  @{username}
                </Link>
                <span className="text-muted">·</span>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="text-muted hover:text-accent transition-colors"
                >
                  Sign out
                </button>
              </span>
            ) : (
              <Link to="/signin" className="text-muted hover:text-accent transition-colors border-l border-border pl-6">
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-2xl mx-auto px-4 pt-12 pb-8 w-full">
        <Outlet />
      </main>

      <footer className="border-t border-border py-3">
        <div className="max-w-2xl mx-auto px-4 text-xs text-muted flex items-center justify-between">
          <span>Press <kbd className="font-mono">?</kbd> for shortcuts</span>
          {!username && location.pathname === '/' && (
            <span>
              <Link to="/signin" className="underline underline-offset-2 decoration-muted/60 hover:text-accent hover:decoration-accent transition-colors">
                Sign in
              </Link> to post
            </span>
          )}
        </div>
      </footer>

      <ShortcutOverlay open={overlayOpen} onClose={() => setOverlayOpen(false)} />
    </div>
  )
}
