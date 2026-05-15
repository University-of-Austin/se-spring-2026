import type { ReactNode } from 'react'
import { ApiError } from '../../api/types'

/**
 * Loading skeleton — three faint serif lines.
 * Used wherever the feed / post / profile is in flight.
 */
export function LoadingRow({ label = 'Loading' }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{ padding: '24px 0', borderBottom: '1px solid var(--hairline)' }}
    >
      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 11,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 14,
        }}
      >
        {label}…
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        <div style={skel(380)} />
        <div style={skel(520)} />
        <div style={skel(280)} />
      </div>
    </div>
  )
}

const skel = (width: number): React.CSSProperties => ({
  height: 12,
  width,
  maxWidth: '100%',
  background: 'var(--hairline)',
  opacity: 0.4,
})

/**
 * Visible error. Eyebrow + body + optional retry slot.
 * 422 array errors hand back fieldError(name) inline; non-field errors
 * land here.
 */
export function ErrorBanner({
  error,
  onRetry,
}: {
  error: unknown
  onRetry?: () => void
}) {
  const msg = describe(error)
  return (
    <div
      role="alert"
      style={{
        padding: '14px 18px',
        border: '1px solid var(--gold)',
        background: 'var(--gold-tint)',
        marginBottom: 24,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        gap: 16,
      }}
    >
      <div>
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 10,
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            color: 'var(--black)',
            marginBottom: 4,
          }}
        >
          Something went wrong
        </div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, lineHeight: 1.5, color: 'var(--black)' }}>
          {msg}
        </div>
      </div>
      {onRetry ? (
        <button type="button" onClick={onRetry} style={retryBtn}>
          Retry
        </button>
      ) : null}
    </div>
  )
}

const retryBtn: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  background: 'transparent',
  border: '1px solid var(--gold)',
  padding: '5px 12px',
  cursor: 'pointer',
}

export function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return 'Unknown error.'
}

/**
 * Empty state.
 */
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div style={{ padding: '48px 0', textAlign: 'center' }}>
      <p
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 11,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 12,
        }}
      >
        {title}
      </p>
      {children ? (
        <p
          style={{
            fontFamily: 'var(--font-serif)',
            fontStyle: 'italic',
            fontSize: 14,
            color: 'var(--muted)',
            maxWidth: 360,
            margin: '0 auto',
          }}
        >
          {children}
        </p>
      ) : null}
    </div>
  )
}
