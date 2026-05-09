// Single user + their posts. Fires GET /users/:u and GET /users/:u/posts in
// parallel via Promise.all. If either rejects (e.g., 404 for unknown user),
// the hook surfaces it via `error` so the page can render a "not found" view.
//
// All four pieces of state (user, posts, loading, error) live in one useState
// bag — they always transition together, so collapsing them into a single
// slot makes the state machine explicit and avoids a lint warning about
// multiple synchronous setStates inside the effect.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { User, Post } from '../types'

type State = {
  user: User | null
  posts: Post[]
  loading: boolean
  error: Error | null
}
const INITIAL: State = { user: null, posts: [], loading: true, error: null }

export function useUser(username: string) {
  const [state, setState] = useState<State>(INITIAL)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    // See usePosts.ts for the full disable rationale.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(INITIAL)

    // Promise.all fires both fetches at the same time and resolves with both
    // results once both succeed. If either rejects, the whole Promise rejects
    // with that error (which is what we want — no partial-data state).
    Promise.all([
      api<User>(`/users/${username}`, { signal: controller.signal }),
      api<Post[]>(`/users/${username}/posts`, { signal: controller.signal }),
    ])
      .then(([user, posts]) =>
        setState({ user, posts, loading: false, error: null })
      )
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setState({ user: null, posts: [], loading: false, error: err })
      })

    return () => controller.abort()
  }, [username, refetchKey])

  return {
    user: state.user,
    posts: state.posts,
    loading: state.loading,
    error: state.error,
    refetch: () => setRefetchKey((k) => k + 1),
  }
}
