import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'bbs_username'

function read(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function useUsername(): {
  username: string
  setUsername: (value: string) => void
  clearUsername: () => void
} {
  const [username, setUsernameState] = useState(read)

  useEffect(() => {
    const onStorage = () => setUsernameState(read())
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const setUsername = useCallback((value: string) => {
    try {
      if (value) {
        localStorage.setItem(STORAGE_KEY, value)
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      /* ignore */
    }
    setUsernameState(read())
  }, [])

  const clearUsername = useCallback(() => {
    setUsername('')
  }, [setUsername])

  return { username, setUsername, clearUsername }
}
