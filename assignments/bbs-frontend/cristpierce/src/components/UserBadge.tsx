import { Link } from 'react-router-dom'
import { Avatar } from './Avatar'
import styles from './UserBadge.module.css'

interface UserBadgeProps {
  username: string
  size?: number
}

/** Avatar + username, linking to that user's profile. */
export function UserBadge({ username, size = 36 }: UserBadgeProps) {
  return (
    <Link to={`/users/${username}`} className={styles.badge}>
      <Avatar username={username} size={size} />
      <span className={styles.name}>{username}</span>
    </Link>
  )
}
