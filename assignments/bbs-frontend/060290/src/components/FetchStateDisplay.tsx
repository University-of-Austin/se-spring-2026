import type { ReactNode } from 'react'
import type { AsyncState } from '../types/asyncState'
import { ServerValidationErrors } from './ServerValidationErrors'
import './FetchStateDisplay.css'

type FetchStateDisplayProps<T> = {
  state: AsyncState<T>
  onRetry?: () => void
  idle?: ReactNode
  children: (data: T) => ReactNode
}

export function FetchStateDisplay<T>({
  state,
  onRetry,
  idle = null,
  children,
}: FetchStateDisplayProps<T>) {
  if (state.phase === 'idle') {
    return <>{idle}</>
  }
  if (state.phase === 'loading') {
    return (
      <div className="fetch-state fetch-state--loading" role="status">
        <p>Loading…</p>
      </div>
    )
  }
  if (state.phase === 'error') {
    return (
      <div className="fetch-state fetch-state--error" role="alert">
        {state.httpStatus === 422 ? (
          <>
            <p className="fetch-state__title">The server could not validate this request.</p>
            <ServerValidationErrors body={state.body} />
          </>
        ) : (
          <p className="fetch-state__message">{state.message}</p>
        )}
        {state.httpStatus === 422 && state.message ? (
          <details className="fetch-state__raw">
            <summary>Technical detail</summary>
            <pre>{state.message}</pre>
          </details>
        ) : null}
        {onRetry ? (
          <button type="button" className="btn btn-secondary" onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </div>
    )
  }
  return <div className="fetch-state fetch-state--success">{children(state.data)}</div>
}
