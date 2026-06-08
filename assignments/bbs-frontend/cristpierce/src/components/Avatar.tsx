import styles from './Avatar.module.css'

// A stable palette; each username maps deterministically to one color so the
// same person looks the same everywhere without any server-side avatar field.
const PALETTE = [
  '#6366f1',
  '#0ea5e9',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
]

function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

interface AvatarProps {
  username: string
  size?: number
}

export function Avatar({ username, size = 34 }: AvatarProps) {
  const color = PALETTE[hashString(username) % PALETTE.length]
  const initials = username.slice(0, 2).toUpperCase()
  return (
    <span
      className={styles.avatar}
      style={{ width: size, height: size, background: color, fontSize: size * 0.4 }}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}
