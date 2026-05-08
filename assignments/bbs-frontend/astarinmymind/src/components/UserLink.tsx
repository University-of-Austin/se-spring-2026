// Clickable @username that goes to /users/:username.
// Used wherever a username appears in the UI.

import { Link } from 'react-router-dom'

export function UserLink({
  username,
  className = '',
}: {
  username: string
  className?: string
}) {
  return (
    <Link
      to={`/users/${username}`}
      className={`text-accent hover:underline ${className}`}
    >
      @{username}
    </Link>
  )
}
