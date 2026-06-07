import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../api/types'

/**
 * Watches every TanStack Query for ApiError(status: 0) — the marker
 * apiFetch sets when the network call itself failed (server down,
 * DNS, CORS preflight fail). When ANY query is in that state, a
 * single global banner appears in the masthead area.
 *
 * Rationale (assignment line item):
 *   The professor explicitly asks "what does your app do if the
 *   backend goes away for 30 seconds." Per-fetch ErrorBanners answer
 *   that locally, but multiple in-flight queries each pop a banner
 *   which reads as panic, not information. One banner that says
 *   "the backend is unreachable" is honest and quiet, and goes away
 *   automatically when any query succeeds again.
 */
export function ConnectionMonitor() {
  const qc = useQueryClient()
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    const cache = qc.getQueryCache()
    const recompute = () => {
      const queries = cache.getAll()
      const anyDown = queries.some((q) => {
        const state = q.state
        if (state.status !== 'error') return false
        const err = state.error
        return err instanceof ApiError && err.status === 0
      })
      const anyOk = queries.some((q) => q.state.status === 'success')
      // Only mark "down" if at least one query is erroring AND nothing
      // is succeeding — avoids false alarms on a single CORS hiccup
      // while other queries are happy.
      setUnreachable(anyDown && !anyOk)
    }
    const unsub = cache.subscribe(() => recompute())
    recompute()
    return () => unsub()
  }, [qc])

  if (!unreachable) return null

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: '#3a1818',
        color: '#f5e1d8',
        padding: '8px 24px',
        fontFamily: 'var(--font-sans)',
        fontSize: 11,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 16,
      }}
    >
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
        <span
          aria-hidden="true"
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#f5e1d8',
            animation: 'connDot 1.4s ease-in-out infinite',
          }}
        />
        Backend unreachable
      </span>
      <button
        type="button"
        onClick={() => qc.invalidateQueries()}
        style={{
          background: 'transparent',
          color: '#f5e1d8',
          border: '1px solid #f5e1d8',
          padding: '3px 12px',
          fontFamily: 'var(--font-sans)',
          fontSize: 10,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          cursor: 'pointer',
        }}
      >
        Retry
      </button>
      <style>{`
        @keyframes connDot {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.35; }
        }
      `}</style>
    </div>
  )
}
