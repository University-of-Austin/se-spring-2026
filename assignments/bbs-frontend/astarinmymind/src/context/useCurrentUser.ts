// Context object + consumer hook for the current signed-in user.
// Lives in a non-JSX file so that UserContext.tsx (the Provider component)
// can be a fast-refresh-friendly components-only file.

import { createContext, useContext } from 'react'

export type UserContextValue = {
  username: string | null
  setUsername: (u: string | null) => void
}

// `null` is the default if no provider is mounted — the consumer hook
// throws a helpful error in that case.
export const UserContext = createContext<UserContextValue | null>(null)

export function useCurrentUser() {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useCurrentUser must be used inside <UserProvider>')
  return ctx
}
