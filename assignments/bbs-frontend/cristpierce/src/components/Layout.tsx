import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Header } from './Header'
import { Toaster } from './ui/Toaster'
import { ShortcutsOverlay } from './ShortcutsOverlay'
import { useTheme } from '../context/ThemeContext'
import { isTypingTarget, useKeydown } from '../hooks/useKeyboard'
import styles from './Layout.module.css'

/*
 * The app shell: skip link, sticky header, the routed page, a footer that
 * advertises the "?" shortcut, the toast stack, and global keyboard handling.
 * Single-key shortcuts are suppressed while typing or while a dialog owns the
 * keyboard, so they never fight the user.
 */
export function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toggleTheme } = useTheme()
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // Announce client-side route changes to assistive tech (no full page load
  // happens, so screen readers otherwise wouldn't know the view changed).
  const [routeAnnouncement, setRouteAnnouncement] = useState('')
  useEffect(() => {
    const path = location.pathname
    const title =
      path === '/'
        ? 'Feed'
        : path === '/users'
          ? 'Users'
          : path.startsWith('/users/')
            ? 'User profile'
            : path.startsWith('/posts/')
              ? 'Post'
              : path === '/compose'
                ? 'Compose'
                : path === '/login'
                  ? 'Sign in'
                  : 'Page'
    setRouteAnnouncement(`${title} page`)
  }, [location.pathname])

  useKeydown((e) => {
    if (e.defaultPrevented) return
    if (e.metaKey || e.ctrlKey || e.altKey) return
    if (isTypingTarget(e.target)) return
    if (document.querySelector('[aria-modal="true"]')) return

    switch (e.key) {
      case '/':
        e.preventDefault()
        document.getElementById('feed-search')?.focus()
        break
      case 'c':
        navigate('/compose')
        break
      case 'h':
        navigate('/')
        break
      case 'u':
        navigate('/users')
        break
      case 't':
        toggleTheme()
        break
      case '?':
        setShortcutsOpen(true)
        break
      default:
        break
    }
  })

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Header />
      <main id="main" className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <span>BBS — Software Engineering A4</span>
        <button type="button" className={styles.helpBtn} onClick={() => setShortcutsOpen(true)}>
          Press <kbd className={styles.kbd}>?</kbd> for keyboard shortcuts
        </button>
      </footer>
      <div aria-live="polite" className="visually-hidden">
        {routeAnnouncement}
      </div>
      <Toaster />
      <ShortcutsOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </>
  )
}
