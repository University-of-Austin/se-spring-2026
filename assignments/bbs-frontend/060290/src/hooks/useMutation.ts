import { useCallback, useState } from 'react'
import { isApiError } from '../api/client'
import type { AsyncState } from '../types/asyncState'

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

export function useMutation<T, Args extends unknown[]>(
  fn: (...args: Args) => Promise<T>,
): {
  state: AsyncState<T>
  mutate: (...args: Args) => Promise<T | undefined>
  reset: () => void
} {
  const [state, setState] = useState<AsyncState<T>>({ phase: 'idle' })

  const mutate = useCallback(
    async (...args: Args) => {
      setState({ phase: 'loading' })
      try {
        const data = await fn(...args)
        setState({ phase: 'success', data })
        return data
      } catch (e: unknown) {
        setState(toErrorState(e))
        return undefined
      }
    },
    [fn],
  )

  const reset = useCallback(() => {
    setState({ phase: 'idle' })
  }, [])

  return { state, mutate, reset }
}
