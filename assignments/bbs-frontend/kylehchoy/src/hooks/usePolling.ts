import { useEffect, useState } from 'react'

/**
 * Visibility-aware refetch interval value.
 *
 * Returns `intervalMs` while the tab is visible, `false` while hidden.
 * Plug into TanStack Query's `refetchInterval`: the query polls while
 * focused and pauses when the user tabs away. On tab-back, Query's
 * default `refetchOnWindowFocus: true` triggers an immediate refetch,
 * so the user never sees stale data.
 *
 * Rationale (README §3): SSE/websockets would require backend lifecycle
 * changes I'm intentionally not making (A2 is frozen). 5s polling at
 * class scale (~250 users × 12 polls/min on the open tab) is well within
 * a SQLite server's budget.
 */
export function usePolling(intervalMs = 5000): number | false {
  const [visible, setVisible] = useState(() =>
    typeof document === 'undefined' ? true : document.visibilityState === 'visible',
  )

  useEffect(() => {
    const onChange = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', onChange)
    return () => document.removeEventListener('visibilitychange', onChange)
  }, [])

  return visible ? intervalMs : false
}
