// Holds the current "logged in" username for the whole app.
// Backed by localStorage so a refresh doesn't kick the user out.
//
// Pattern: <UserProvider> wraps the app once (in App.tsx). Any component
// then calls `useCurrentUser()` to read or update the username. No prop drilling.

import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

// The shape of what useCurrentUser() returns.
type UserContextValue = {
  username: string | null
  setUsername: (u: string | null) => void
}

// The Context object itself. `null` is the default if no provider is mounted —
// we throw a helpful error in that case (see useCurrentUser below).
const UserContext = createContext<UserContextValue | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  // Lazy initializer: the function only runs once, on first render.
  // Reads the saved username (if any) so refreshes restore identity.
  const [username, setState] = useState<string | null>(
    () => localStorage.getItem('username')
  )

  // Single setter that writes to both React state AND localStorage in one move,
  // so they never drift out of sync.
  const setUsername = (u: string | null) => {
    setState(u)
    if (u) localStorage.setItem('username', u)
    else localStorage.removeItem('username')
  }

  return (
    <UserContext.Provider value={{ username, setUsername }}>
      {children}
    </UserContext.Provider>
  )
}

// Custom hook every component uses to read/update the current user.
export function useCurrentUser() {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useCurrentUser must be used inside <UserProvider>')
  return ctx
}
