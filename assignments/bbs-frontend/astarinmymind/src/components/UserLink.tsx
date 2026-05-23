// Clickable @username that goes to /users/:username.
// Kepano-style inline content link: underlined by default with a muted
// underline; hover flips text + underline to the accent (turquoise).

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
      className={`underline underline-offset-2 decoration-muted/60 hover:text-accent hover:decoration-accent transition-colors ${className}`}
    >
      @{username}
    </Link>
  )
}
