import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useCurrentUser } from '../context/UserContext';
import { ThemeToggle } from './ThemeToggle';
import { KeyboardHelp } from './KeyboardHelp';
import { useGlobalShortcuts } from '../hooks/useGlobalShortcuts';
import { useFocusOnRouteChange } from '../hooks/useFocusOnRouteChange';

export function Layout() {
  const { username } = useCurrentUser();
  const [helpOpen, setHelpOpen] = useState<boolean>(false);

  useGlobalShortcuts({ onHelp: () => setHelpOpen(true) });
  useFocusOnRouteChange();

  return (
    <div className="app-shell">
      <header className="header">
        <div className="header__inner">
          <Link to="/" className="header__brand">BBS</Link>
          <div className="header__right">
            <ThemeToggle />
            {username ? (
              <Link to="/login" className="user-pill" title={`Signed in as @${username}`}>
                @{username}
              </Link>
            ) : (
              <Link to="/login" className="btn btn--sm btn--primary">Sign in</Link>
            )}
          </div>
        </div>
      </header>

      <nav className="nav" aria-label="Primary">
        <div className="nav__inner">
          <NavLink to="/" end className="nav__link">Feed</NavLink>
          <NavLink to="/users" className="nav__link">Users</NavLink>
          {username && (
            <NavLink to={`/users/${username}`} className="nav__link">
              My profile
            </NavLink>
          )}
          <NavLink to="/login" className="nav__link">
            {username ? 'Switch user' : 'Sign in'}
          </NavLink>
        </div>
      </nav>

      <main className="main" id="main">
        <Outlet />
      </main>

      <footer className="footer">
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          onClick={() => setHelpOpen(true)}
          aria-label="Show keyboard shortcuts"
        >
          ? Keyboard shortcuts
        </button>
      </footer>

      <KeyboardHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
