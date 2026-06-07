// Single post by id. Same pattern as usePosts/useUsers/useUser:
// AbortController guard, refetchKey, three-state return.
//
// All three pieces of state (post, loading, error) live in one useState bag.
// They always transition together (start → loading=true; resolve → both
// loading and post set; reject → loading and error set), so collapsing them
// into one slot makes the state machine explicit and avoids a lint warning
// about multiple synchronous setStates inside the effect.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Post } from '../types'

type State = { post: Post | null; loading: boolean; error: Error | null }
const INITIAL: State = { post: null, loading: true, error: null }

export function usePost(id: number) {
  const [state, setState] = useState<State>(INITIAL)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    // Disable rationale documented in usePosts.ts — same reasoning here:
    // the rule rejects any synchronous setState inside an effect, but
    // resetting state at fetch start is fundamental to the hand-rolled
    // fetch-with-spinner pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(INITIAL)

    api<Post>(`/posts/${id}`, { signal: controller.signal })
      .then((post) => setState({ post, loading: false, error: null }))
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setState({ post: null, loading: false, error: err })
      })

    return () => controller.abort()
  }, [id, refetchKey])

  return {
    post: state.post,
    loading: state.loading,
    error: state.error,
    refetch: () => setRefetchKey((k) => k + 1),
  }
}
