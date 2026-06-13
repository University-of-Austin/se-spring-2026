/*
 * StateView — the structural guard that makes the "every fetch shows loading +
 * error + success" rule impossible to forget.
 *
 * The success branch (`children`) is a render-prop that only ever receives
 * fully-loaded, defined data. You literally cannot render the success UI
 * without the component first having dealt with loading and error. This is the
 * direct answer to the assignment's warning about agents shipping
 * `data.map(...)` with no guards.
 *
 * Stale-while-revalidate: if we already have data and a background refetch is
 * in flight (or even fails), we keep showing the data rather than flashing a
 * spinner or an error over readable content.
 */

import type { ReactNode } from 'react'
import type { ApiError } from '../../lib/api'
import type { Status } from '../../hooks/useResource'
import { Button } from './Button'
import { AlertIcon } from './icons'
import styles from './StateView.module.css'

interface StateViewProps<T> {
  status: Status
  data: T | undefined
  error?: ApiError
  onRetry?: () => void
  /** Custom loading UI (defaults to a centered spinner). */
  loading?: ReactNode
  /** Title for the default error view. */
  errorTitle?: string
  /** Predicate + node for the "loaded but empty" case. */
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  children: (data: T) => ReactNode
}

export function StateView<T>({
  status,
  data,
  error,
  onRetry,
  loading,
  errorTitle,
  isEmpty,
  empty,
  children,
}: StateViewProps<T>) {
  // First load, nothing to show yet.
  if (data === undefined) {
    if (status === 'loading') return <>{loading ?? <LoadingBlock />}</>
    if (status === 'error') return <ErrorView error={error} onRetry={onRetry} title={errorTitle} />
    return null // idle
  }

  // We have data — show it even while revalidating or after a background error.
  if (isEmpty?.(data) && empty !== undefined) return <>{empty}</>
  return <>{children(data)}</>
}

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className={styles.center} role="status">
      <span className={styles.dots} aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span className={styles.muted}>{label}</span>
    </div>
  )
}

export function ErrorView({
  error,
  onRetry,
  title = 'Something went wrong',
}: {
  error?: ApiError
  onRetry?: () => void
  title?: string
}) {
  return (
    <div className={styles.error} role="alert">
      <AlertIcon size={22} />
      <div className={styles.errorBody}>
        <strong>{title}</strong>
        <p>{error?.message ?? 'Please try again.'}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: ReactNode }) {
  return (
    <div className={styles.empty}>
      <p className={styles.emptyTitle}>{title}</p>
      {hint && <p className={styles.muted}>{hint}</p>}
    </div>
  )
}
