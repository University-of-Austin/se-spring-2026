import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { AsyncState } from '../types/asyncState'
import { isApiError } from '../api/client'

function toErrorState(e: unknown): AsyncState<never> {
  if (isApiError(e)) {
    return {
      phase: 'error',
      message: e.message,
      httpStatus: e.status,
      body: e.body,
    }
  }
  if (e instanceof Error) {
    return { phase: 'error', message: e.message }
  }
  return { phase: 'error', message: 'Something went wrong' }
}

/**
 * Runs `fetcher` when `cacheKey` changes. Starts in `loading`.
 * `fetcher` may close over props; keep `cacheKey` in sync with those inputs.
 */
export function useMountFetch<T>(
  cacheKey: string,
  fetcher: () => Promise<T>,
): { state: AsyncState<T>; refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ phase: 'loading' })
  const fetcherRef = useRef(fetcher)

  useLayoutEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  const load = useCallback(() => {
    setState({ phase: 'loading' })
    fetcherRef
      .current()
      .then((data) => {
        setState({ phase: 'success', data })
      })
      .catch((e: unknown) => {
        setState(toErrorState(e))
      })
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch when cacheKey changes; load also used for Retry
    load()
  }, [cacheKey, load])

  return { state, refetch: load }
}
