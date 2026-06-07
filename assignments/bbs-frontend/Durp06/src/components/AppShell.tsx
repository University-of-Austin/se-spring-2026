import { useCallback, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useIdentity } from '../identity/IdentityContext';
import { useTheme } from '../theme/ThemeContext';
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut';
import { HelpOverlay } from './HelpOverlay';
import { ToastTray } from '../hooks/useToast';

export function AppShell() {
  const { username, setUsername } = useIdentity();
  const { theme, toggle } = useTheme();
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();
  const gPressed = useRef<number | null>(null);

  // ? shortcut for help (assignment silver requirement: at least one shortcut
  // beyond Cmd+Enter, surfaced visibly).
  useKeyboardShortcut('?', useCallback(() => setHelpOpen((o) => !o), []));

  // t toggles theme.
  useKeyboardShortcut('t', useCallback(() => toggle(), [toggle]));

  // n goes to the compose page (only when not already in a text input).
  useKeyboardShortcut(
    'n',
    useCallback(() => navigate('/compose'), [navigate]),
  );

  // g-prefix navigation: press 'g' then 'f' (feed) or 'u' (users) within 1s.
  useKeyboardShortcut(
    'g',
    useCallback(() => {
      gPressed.current = window.setTimeout(() => {
        gPressed.current = null;
      }, 1000) as unknown as number;
    }, []),
  );
  useKeyboardShortcut(
    'f',
    useCallback(() => {
      if (gPressed.current !== null) {
        navigate('/');
        gPressed.current = null;
      }
    }, [navigate]),
  );
  useKeyboardShortcut(
    'u',
    useCallback(() => {
      if (gPressed.current !== null) {
        navigate('/users');
        gPressed.current = null;
      }
    }, [navigate]),
  );

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          <Link to="/" className="app__brand-link">
            BBS<span className="app__brand-dot">.</span>
          </Link>
        </div>
        <nav className="app__nav" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'navlink navlink--active' : 'navlink')}>
            Feed
          </NavLink>
          <NavLink to="/users" className={({ isActive }) => (isActive ? 'navlink navlink--active' : 'navlink')}>
            Users
          </NavLink>
          <NavLink to="/compose" className={({ isActive }) => (isActive ? 'navlink navlink--active' : 'navlink')}>
            Compose
          </NavLink>
        </nav>
        <div className="app__identity">
          {username ? (
            <>
              <Link to={`/users/${encodeURIComponent(username)}`} className="identity__chip">
                @{username}
              </Link>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setUsername(null)}
                aria-label="Sign out"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link to="/signup" className="btn btn--primary btn--sm">
              Sign in
            </Link>
          )}
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            onClick={toggle}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            onClick={() => setHelpOpen(true)}
            aria-label="Show keyboard shortcuts"
            title="Shortcuts (?)"
          >
            ?
          </button>
        </div>
      </header>
      <main className="app__main">
        <Outlet />
      </main>
      <footer className="app__footer">
        <span>
          Press <kbd>?</kbd> for shortcuts
        </span>
      </footer>
      <HelpOverlay open={helpOpen} onClose={() => setHelpOpen(false)} />
      <ToastTray />
    </div>
  );
}
