// Provider for the current signed-in user. Backed by localStorage so a
// refresh doesn't kick the user out.
//
// Pattern: <UserProvider> wraps the app once (in App.tsx). Any component
// reads/updates the username via `useCurrentUser()` from ./useCurrentUser.
// The Context object itself lives in that file (alongside the hook) so
// this file can stay components-only — fast-refresh stays granular.

import { useState } from 'react'
import type { ReactNode } from 'react'
import { UserContext } from './useCurrentUser'

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
