import { Link, NavLink } from 'react-router-dom'
import { useIdentity } from '../context/IdentityContext'
import { useTheme } from '../context/ThemeContext'
import { Avatar } from './Avatar'
import { Button } from './ui/Button'
import { HomeIcon, MoonIcon, PlusIcon, SunIcon, UsersIcon } from './ui/icons'
import styles from './Header.module.css'

export function Header() {
  const { username, isLoggedIn } = useIdentity()
  const { theme, toggleTheme } = useTheme()

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `${styles.navlink} ${isActive ? styles.active : ''}`

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to="/" className={styles.brand} aria-label="BBS — home">
          <span className={styles.mark} aria-hidden="true" />
          <span className={styles.brandText}>BBS</span>
        </Link>

        <nav className={styles.nav} aria-label="Primary">
          <NavLink to="/" end className={navClass}>
            <HomeIcon size={17} />
            <span className={styles.navlabel}>Feed</span>
          </NavLink>
          <NavLink to="/users" className={navClass}>
            <UsersIcon size={17} />
            <span className={styles.navlabel}>Users</span>
          </NavLink>
        </nav>

        <div className={styles.right}>
          <NavLink to="/compose" className={styles.compose}>
            <PlusIcon size={16} />
            <span className={styles.navlabel}>Post</span>
          </NavLink>

          <Button
            variant="ghost"
            size="sm"
            iconOnly
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            title="Toggle theme (t)"
            onClick={toggleTheme}
          >
            {theme === 'dark' ? <SunIcon size={18} /> : <MoonIcon size={18} />}
          </Button>

          {isLoggedIn ? (
            <div className={styles.account}>
              <Link
                to={`/users/${username}`}
                className={styles.identity}
                title={`Signed in as ${username} — view profile`}
              >
                <Avatar username={username!} size={28} />
                <span className={styles.username}>{username}</span>
              </Link>
              <Link to="/login" className={styles.switch}>
                Switch
              </Link>
            </div>
          ) : (
            <Link to="/login" className={styles.signin}>
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
