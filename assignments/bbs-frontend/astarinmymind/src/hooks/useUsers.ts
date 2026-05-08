// List all users. Same pattern as usePosts (AbortController guard, refetchKey
// for manual reload, three-state return). Only difference: no filters.

import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { User } from '../types'

export function useUsers() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [refetchKey, setRefetchKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    api<User[]>('/users', { signal: controller.signal })
      .then(setUsers)
      .catch((err: Error) => {
        if (err.name === 'AbortError' || controller.signal.aborted) return
        setError(err)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [refetchKey])

  return {
    users,
    loading,
    error,
    refetch: () => setRefetchKey(k => k + 1),
  }
}
