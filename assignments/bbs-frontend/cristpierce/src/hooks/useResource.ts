/*
 * The async primitives every data-driven component is built on.
 *
 * useResource(): a small state machine — idle | loading | success | error —
 * for a single GET. It auto-runs on mount and whenever `deps` change, aborts
 * the in-flight request on change/unmount (so a fast-typed search never lands
 * a stale response), keeps the previous data visible during a reload, and can
 * refetch on window focus (so a tab you left open and came back to is fresh).
 *
 * useMutation(): wraps a write (POST/PATCH/DELETE) and exposes `pending`, which
 * is what disables buttons to prevent the classic double-click double-submit.
 *
 * Components consume these instead of touching fetch or even the api module
 * directly for reads, which is why no component has to hand-roll loading/error
 * handling — the type system won't let you read `data` without acknowledging
 * the other states.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { DependencyList } from 'react'
import { ApiError } from '../lib/api'

export type Status = 'idle' | 'loading' | 'success' | 'error'

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  const message =
    err instanceof Error ? err.message : typeof err === 'string' ? err : 'Something went wrong.'
  return new ApiError({ status: 0, message, isNetwork: true })
}

export interface Resource<T> {
  status: Status
  data: T | undefined
  error: ApiError | undefined
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  refetch: () => void
  /** Imperatively overwrite the cached data — used for optimistic updates. */
  setData: (updater: T | ((prev: T | undefined) => T)) => void
}

interface ResourceOptions {
  /** When false, the resource stays idle and never fetches (e.g. no username). */
  enabled?: boolean
  /** Refetch when the tab regains focus. Default true. */
  refetchOnFocus?: boolean
}

export function useResource<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
  options: ResourceOptions = {},
): Resource<T> {
  const { enabled = true, refetchOnFocus = true } = options

  const [nonce, setNonce] = useState(0)
  const [state, setState] = useState<{
    status: Status
    data: T | undefined
    error: ApiError | undefined
  }>(() => ({ status: enabled ? 'loading' : 'idle', data: undefined, error: undefined }))

  // Hold the latest fetcher in a ref so a new closure each render doesn't
  // retrigger the effect; the effect re-runs only on deps/nonce/enabled.
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  useEffect(() => {
    if (!enabled) {
      setState({ status: 'idle', data: undefined, error: undefined })
      return
    }
    let active = true
    const controller = new AbortController()
    setState((s) => ({ status: 'loading', data: s.data, error: undefined }))

    fetcherRef.current(controller.signal)
      .then((data) => {
        if (active) setState({ status: 'success', data, error: undefined })
      })
      .catch((err: unknown) => {
        if (!active || controller.signal.aborted) return
        if (err instanceof DOMException && err.name === 'AbortError') return
        setState((s) => ({ status: 'error', data: s.data, error: toApiError(err) }))
      })

    return () => {
      active = false
      controller.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, nonce])

  useEffect(() => {
    if (!enabled || !refetchOnFocus) return
    const onVisible = () => {
      if (document.visibilityState === 'visible') setNonce((n) => n + 1)
    }
    window.addEventListener('focus', onVisible)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('focus', onVisible)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [enabled, refetchOnFocus])

  const refetch = useCallback(() => setNonce((n) => n + 1), [])

  const setData = useCallback((updater: T | ((prev: T | undefined) => T)) => {
    setState((s) => {
      const next =
        typeof updater === 'function'
          ? (updater as (prev: T | undefined) => T)(s.data)
          : updater
      return { status: 'success', data: next, error: undefined }
    })
  }, [])

  return {
    status: state.status,
    data: state.data,
    error: state.error,
    isLoading: state.status === 'loading',
    isError: state.status === 'error',
    isSuccess: state.status === 'success',
    refetch,
    setData,
  }
}

export interface Mutation<TArgs extends unknown[], TResult> {
  run: (...args: TArgs) => Promise<TResult>
  pending: boolean
  error: ApiError | undefined
  reset: () => void
}

export function useMutation<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
): Mutation<TArgs, TResult> {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<ApiError | undefined>(undefined)

  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  }, [fn])

  const run = useCallback(async (...args: TArgs) => {
    setPending(true)
    setError(undefined)
    try {
      return await fnRef.current(...args)
    } catch (err) {
      const apiErr = toApiError(err)
      setError(apiErr)
      throw apiErr
    } finally {
      setPending(false)
    }
  }, [])

  const reset = useCallback(() => setError(undefined), [])

  return { run, pending, error, reset }
}
