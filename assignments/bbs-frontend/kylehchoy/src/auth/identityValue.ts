import { createContext } from 'react'

export interface IdentityValue {
  username: string | null
  setUsername: (next: string | null) => void
  clear: () => void
}

export const IdentityContext = createContext<IdentityValue | null>(null)
