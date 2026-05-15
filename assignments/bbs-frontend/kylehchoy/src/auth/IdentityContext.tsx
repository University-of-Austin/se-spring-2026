import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { setIdentity as setApiIdentity } from '../api/client'
import { isValidUsername } from '../lib/validation'
import { IdentityContext, type IdentityValue } from './identityValue'

const STORAGE_KEY = 'thenetwork.username'

function readStorage(): string | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (!v) return null
    return isValidUsername(v) ? v : null
  } catch {
    return null
  }
}

function writeStorage(v: string | null): void {
  try {
    if (v === null) localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, v)
  } catch {
    // private mode / quota — silently ignore. X-Username is preference, not auth.
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [username, setState] = useState<string | null>(() => readStorage())

  // Keep the api/client identity in sync so every fetch sees the current user.
  useEffect(() => {
    setApiIdentity(username)
  }, [username])

  const setUsername = useCallback((next: string | null) => {
    if (next !== null && !isValidUsername(next)) return
    writeStorage(next)
    setState(next)
  }, [])

  const clear = useCallback(() => {
    writeStorage(null)
    setState(null)
  }, [])

  const value = useMemo<IdentityValue>(
    () => ({ username, setUsername, clear }),
    [username, setUsername, clear],
  )

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}
