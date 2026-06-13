/*
 * Human-friendly timestamps. A2 stores naive local ISO strings
 * (datetime.now().isoformat()), which the browser parses as local time — fine
 * for this app since the dev backend and browser share a clock.
 *
 * `now` is injectable so the formatting is deterministic under test.
 */

export function relativeTime(iso: string, now: number = Date.now()): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''

  const diffMs = now - t
  // Small clock skew between server and client can make a fresh post look
  // slightly "in the future"; clamp to "just now".
  if (diffMs < 0) return 'just now'

  const sec = Math.floor(diffMs / 1000)
  if (sec < 5) return 'just now'
  if (sec < 60) return `${sec}s ago`

  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`

  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`

  const day = Math.floor(hr / 24)
  if (day < 7) return `${day}d ago`

  const wk = Math.floor(day / 7)
  if (wk < 5) return `${wk}w ago`

  return new Date(t).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Current time as a naive-local ISO string, matching the backend's
 * datetime.now().isoformat() (no timezone suffix). Used for optimistic posts so
 * their timestamps sort and compare consistently with server timestamps.
 */
export function localIsoNow(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

/** Full timestamp for tooltips / title attributes. */
export function absoluteTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}
