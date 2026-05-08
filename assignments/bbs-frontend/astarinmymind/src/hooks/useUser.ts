// Single user + their posts. Fires GET /users/:u and GET /users/:u/posts in
// parallel via Promise.all. If either rejects (e.g., 404 for unknown user),
// the hook surfaces it via `error` so the page can render a "not found" view.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { User, Post } from '../types'

export function useUser(username: string) {
  const [user, setUser] = useState<User | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    // Promise.all fires both fetches at the same time and resolves with both
    // results once both succeed. If either rejects, the whole Promise rejects
    // with that error (which is what we want — no partial-data state).
    Promise.all([
      api<User>(`/users/${username}`, { signal: controller.signal }),
      api<Post[]>(`/users/${username}/posts`, { signal: controller.signal }),
    ])
      .then(([userData, userPosts]) => {
        setUser(userData)
        setPosts(userPosts)
      })
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setError(err)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [username, refetchKey])

  return {
    user,
    posts,
    loading,
    error,
    refetch: () => setRefetchKey(k => k + 1),
  }
}
