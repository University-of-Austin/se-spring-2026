// Single post by id. Same pattern as usePosts/useUsers/useUser:
// AbortController guard, refetchKey, three-state return.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Post } from '../types'

export function usePost(id: number) {
  const [post, setPost] = useState<Post | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    api<Post>(`/posts/${id}`, { signal: controller.signal })
      .then(setPost)
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setError(err)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [id, refetchKey])

  return {
    post,
    loading,
    error,
    refetch: () => setRefetchKey(k => k + 1),
  }
}
