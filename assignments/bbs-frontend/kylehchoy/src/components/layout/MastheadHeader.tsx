import { Link } from 'react-router-dom'
import { useIdentity } from '../../auth/IdentityContext'
import { LiveDot } from './LiveDot'

/**
 * Masthead: gold bar across the top.
 *
 * Layer 1 (Facebook 2004): solid color bar, lowercase wordmark left,
 * nav links flush right reading literally "my profile | my friends |
 * my privacy | logout".
 *
 * Layer 2 (UATX): gold #B89A5F (not blue), Antonio condensed sans, tracked
 * uppercase nav. The four Facebook nav links map onto real routes:
 *   my profile  -> /users/<current-identity> (or /signup if none)
 *   my friends  -> /users  (the directory)
 *   my privacy  -> /signup (switch identity)
 *   logout      -> clear identity, stay on current page
 */
export function MastheadHeader() {
  const { username, clear } = useIdentity()

  const onLogout = () => {
    clear()
    // Stay on the current page; views handle "no identity" themselves.
  }

  const profilePath = username
    ? `/users/${encodeURIComponent(username)}`
    : '/signup'

  return (
    <header
      style={{
        background: 'var(--gold)',
        height: 40,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        color: 'var(--white)',
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Link
          to="/"
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 24,
            fontWeight: 500,
            textDecoration: 'none',
            color: 'var(--white)',
            letterSpacing: '-0.005em',
          }}
        >
          thenetwork
        </Link>
        <LiveDot />
      </span>

      <nav
        aria-label="Primary"
        style={{
          display: 'flex',
          gap: 22,
          fontFamily: 'var(--font-sans)',
          fontSize: 11,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
        }}
      >
        <Link to={profilePath} style={navLink}>my profile</Link>
        <Link to="/users" style={navLink}>my friends</Link>
        <Link to="/signup" style={navLink}>my privacy</Link>
        {username ? (
          <button
            type="button"
            onClick={onLogout}
            aria-label="Log out and clear identity"
            style={{ ...navLink, background: 'transparent', border: 0, cursor: 'pointer', padding: 0 }}
          >
            logout
          </button>
        ) : (
          <Link to="/signup" style={navLink}>login</Link>
        )}
      </nav>
    </header>
  )
}

const navLink: React.CSSProperties = {
  color: 'var(--white)',
  textDecoration: 'none',
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
}
