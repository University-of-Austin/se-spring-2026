// Custom hook that owns the loading/error/data state for GET /posts.
// Components call this and get { posts, loading, error, refetch } back.
// Includes optimistic helpers (used by ComposeForm in Phase 4).

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Post } from '../types'

type Filters = { q?: string; limit?: number; offset?: number }

export function usePosts(filters: Filters = {}) {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    // Race-condition guard via AbortController (Lecture 6.1, slide 5).
    // If filters change while a fetch is in flight, abort the old one so its
    // (now-stale) response can't overwrite the newer fetch's data. The browser
    // actually cancels the network request — not just ignores its result.
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    // Build the query string from whichever filters are actually set.
    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.limit !== undefined) params.set('limit', String(filters.limit))
    if (filters.offset !== undefined) params.set('offset', String(filters.offset))
    const qs = params.toString() ? `?${params}` : ''

    api<Post[]>(`/posts${qs}`, { signal: controller.signal })
      .then(setPosts)
      .catch((err: Error) => {
        // AbortError = expected (we triggered the abort ourselves), ignore.
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setError(err)
      })
      .finally(() => {
        // Don't clobber the next effect's loading=true if we were aborted.
        if (!controller.signal.aborted) setLoading(false)
      })

    // Cleanup: runs before the next effect (or on unmount).
    return () => controller.abort()
  }, [filters.q, filters.limit, filters.offset, refetchKey])

  // Optimistic helpers — used by ComposeForm in Phase 4 to prepend a fake post
  // immediately, then remove it once the server confirms (or fails).
  const addOptimistic = (post: Post) => setPosts(prev => [post, ...prev])
  const removeOptimistic = (id: number) => setPosts(prev => prev.filter(p => p.id !== id))

  return {
    posts,
    loading,
    error,
    refetch: () => setRefetchKey(k => k + 1),
    addOptimistic,
    removeOptimistic,
  }
}
