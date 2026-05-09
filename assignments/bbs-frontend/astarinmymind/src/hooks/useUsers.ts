// List all users. Same pattern as the other read hooks:
// single useState bag for users/loading/error so the effect dispatches one
// state transition per fetch lifecycle (start → resolve|reject), instead of
// two synchronous setStates that the lint rule flags as cascading renders.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { User } from '../types'

type State = { users: User[]; loading: boolean; error: Error | null }
const INITIAL: State = { users: [], loading: true, error: null }

export function useUsers() {
  const [state, setState] = useState<State>(INITIAL)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    // See usePosts.ts for the full disable rationale.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(INITIAL)

    api<User[]>('/users', { signal: controller.signal })
      .then((users) => setState({ users, loading: false, error: null }))
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setState({ users: [], loading: false, error: err })
      })

    return () => controller.abort()
  }, [refetchKey])

  return {
    users: state.users,
    loading: state.loading,
    error: state.error,
    refetch: () => setRefetchKey((k) => k + 1),
  }
}
