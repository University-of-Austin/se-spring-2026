import { useCallback, useEffect, useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useUsername } from '../hooks/useUsername'
import { KeyboardShortcutsDialog } from './KeyboardShortcutsDialog'
import './Layout.css'

const nav = [
  { to: '/', label: 'Feed' },
  { to: '/compose', label: 'Compose' },
  { to: '/users', label: 'Users' },
  { to: '/account', label: 'Sign up / user' },
]

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) {
    return false
  }
  const tag = el.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
    return true
  }
  return el.isContentEditable
}

export function Layout() {
  const { username } = useUsername()
  const location = useLocation()
  const navigate = useNavigate()
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  const focusFeedSearch = useCallback(() => {
    if (location.pathname !== '/') {
      void navigate('/')
    }
    requestAnimationFrame(() => {
      document.getElementById('feed-search')?.focus()
    })
  }, [location.pathname, navigate])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && shortcutsOpen) {
        e.preventDefault()
        setShortcutsOpen(false)
        return
      }
      if (isTypingTarget(e.target)) {
        return
      }
      if (e.key === '?' && e.shiftKey) {
        e.preventDefault()
        setShortcutsOpen(true)
        return
      }
      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault()
        focusFeedSearch()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [focusFeedSearch, shortcutsOpen])

  return (
    <div className="layout">
      <header className="layout-header">
        <div className="layout-brand">
          <NavLink to="/" className="layout-title">
            BBS
          </NavLink>
          <span className="layout-user" aria-live="polite">
            {username ? (
              <>
                Posting as <strong>{username}</strong>
              </>
            ) : (
              <>No user selected — set one on Sign up / user</>
            )}
          </span>
        </div>
        <nav className="layout-nav" aria-label="Main">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                isActive ? 'layout-link layout-link--active' : 'layout-link'
              }
              end={to === '/'}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="layout-main">
        {!username ? (
          location.pathname === '/account' ? (
            <>
              <div className="layout-setup-prompt" role="status">
                <h2 className="layout-setup-prompt__title">Set your username first</h2>
                <p className="layout-setup-prompt__text">
                  Sign up for a new account or switch to an existing username below. You need a
                  posting name before using the rest of the app.
                </p>
              </div>
              <Outlet />
            </>
          ) : (
            <Navigate to="/account" replace />
          )
        ) : (
          <Outlet />
        )}
      </main>
      <footer className="layout-footer">
        <button
          type="button"
          className="layout-footer__btn"
          onClick={() => setShortcutsOpen(true)}
        >
          Keyboard shortcuts (Shift+?)
        </button>
      </footer>
      <KeyboardShortcutsDialog open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  )
}
