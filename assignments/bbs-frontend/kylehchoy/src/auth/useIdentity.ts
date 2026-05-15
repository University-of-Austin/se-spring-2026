import { useContext } from 'react'
import { IdentityContext, type IdentityValue } from './identityValue'

/**
 * Hook to read or mutate the current identity.
 * Split from IdentityContext.tsx so the context file exports only the
 * Provider component — keeps Vite's Fast Refresh happy.
 */
export function useIdentity(): IdentityValue {
  const ctx = useContext(IdentityContext)
  if (!ctx) {
    throw new Error('useIdentity must be used inside <IdentityProvider>')
  }
  return ctx
}
