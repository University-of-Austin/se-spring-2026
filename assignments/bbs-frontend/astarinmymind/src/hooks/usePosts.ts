// Custom hook that owns the loading/error/data state for GET /posts.
// Components call this and get { posts, loading, error, refetch } back.
// Includes optimistic helpers (used by ComposeForm in Phase 4).
//
// State design: posts/loading/error/lastFetchSize live together in one
// useState bag so each fetch lifecycle (start → resolve|reject) can dispatch
// a single state transition. Splitting them into separate useState slots
// would mean multiple synchronous setStates in the effect, which the React
// lint rule flags as a cascading-render smell — and which is genuinely a
// missed opportunity to make the state machine explicit.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Post } from '../types'

type Filters = { q?: string; limit?: number; offset?: number }

type State = {
  posts: Post[]
  loading: boolean
  error: Error | null
  // Size of the most recent fetch's response — pages use this to decide
  // whether a "Load more" sentinel should still be shown (full page = maybe more).
  lastFetchSize: number | null
}

const INITIAL: State = { posts: [], loading: true, error: null, lastFetchSize: null }

export function usePosts(filters: Filters = {}) {
  const [state, setState] = useState<State>(INITIAL)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    // Race-condition guard via AbortController (Lecture 6.1, slide 5).
    // If filters change while a fetch is in flight, abort the old one so its
    // (now-stale) response can't overwrite the newer fetch's data. The browser
    // actually cancels the network request — not just ignores its result.
    const controller = new AbortController()
    // Keep existing posts visible during a refetch — only flip loading+error.
    // We don't reset to INITIAL here because for "Load more" (offset > 0) we
    // want the prior page still on screen while the next one is fetched.
    //
    // The lint rule below objects to ANY synchronous setState inside an
    // effect, regardless of whether it's one call or many. That stance is
    // fundamentally incompatible with hand-rolled fetch + spinner: we have
    // to flip `loading` true at the start of each request so the UI shows
    // a pending state. The rule is steering us toward Suspense or a data
    // library (TanStack Query / SWR), which would replace this hook
    // wholesale; until then, the suppression is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((prev) => ({ ...prev, loading: true, error: null }))

    // Build the query string from whichever filters are actually set.
    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.limit !== undefined) params.set('limit', String(filters.limit))
    if (filters.offset !== undefined) params.set('offset', String(filters.offset))
    const qs = params.toString() ? `?${params}` : ''

    api<Post[]>(`/posts${qs}`, { signal: controller.signal })
      .then((data) => {
        setState((prev) => ({
          // offset > 0 means "Load more" — append the new page to existing posts.
          // offset === 0 (or undefined) means "fresh load / search" — replace.
          posts:
            filters.offset && filters.offset > 0
              ? [...prev.posts, ...data]
              : data,
          loading: false,
          error: null,
          lastFetchSize: data.length,
        }))
      })
      .catch((err: Error) => {
        // AbortError = expected (we triggered the abort ourselves), ignore.
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setState((prev) => ({ ...prev, loading: false, error: err }))
      })

    return () => controller.abort()
  }, [filters.q, filters.limit, filters.offset, refetchKey])

  // Optimistic helpers — used by ComposeForm in Phase 4 to prepend a fake post
  // immediately, then remove it once the server confirms (or fails).
  const addOptimistic = (post: Post) =>
    setState((prev) => ({ ...prev, posts: [post, ...prev.posts] }))
  const removeOptimistic = (id: number) =>
    setState((prev) => ({ ...prev, posts: prev.posts.filter((p) => p.id !== id) }))

  return {
    posts: state.posts,
    loading: state.loading,
    error: state.error,
    lastFetchSize: state.lastFetchSize,
    refetch: () => setRefetchKey((k) => k + 1),
    addOptimistic,
    removeOptimistic,
  }
}
