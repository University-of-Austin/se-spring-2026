/* eslint-disable react-refresh/only-export-components -- Provider + hook are
   intentionally colocated; this only affects HMR granularity, not correctness. */

/*
 * Who am I "logged in" as. A2's X-Username is an honor-system identifier, not
 * real auth, so identity here is just a persisted preference: the chosen
 * username lives in localStorage and is restored on refresh. It also syncs
 * across tabs via the `storage` event, so switching users in one tab updates
 * the others.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import type { ReactNode } from 'react'

const STORAGE_KEY = 'bbs:username'

interface IdentityValue {
  username: string | null
  isLoggedIn: boolean
  /** Set (or clear) the active username, persisting to localStorage. */
  setUsername: (username: string | null) => void
  logout: () => void
}

const IdentityContext = createContext<IdentityValue | null>(null)

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(readStored)

  const setUsername = useCallback((next: string | null) => {
    setUsernameState(next)
    try {
      if (next) localStorage.setItem(STORAGE_KEY, next)
      else localStorage.removeItem(STORAGE_KEY)
    } catch {
      // localStorage can throw in private mode / when full — identity simply
      // won't persist across refresh, which is an acceptable degradation.
    }
  }, [])

  const logout = useCallback(() => setUsername(null), [setUsername])

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setUsernameState(e.newValue)
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const value = useMemo<IdentityValue>(
    () => ({ username, isLoggedIn: username !== null, setUsername, logout }),
    [username, setUsername, logout],
  )

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}

export function useIdentity(): IdentityValue {
  const ctx = useContext(IdentityContext)
  if (!ctx) throw new Error('useIdentity must be used within an IdentityProvider')
  return ctx
}
