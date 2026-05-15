import { describe, expect, it } from 'vitest'
import { act, render, renderHook } from '@testing-library/react'
import { IdentityProvider, useIdentity } from '../../src/auth/IdentityContext'

function wrap({ children }: { children: React.ReactNode }) {
  return <IdentityProvider>{children}</IdentityProvider>
}

describe('IdentityContext', () => {
  it('persists a valid username to localStorage', () => {
    const { result } = renderHook(() => useIdentity(), { wrapper: wrap })
    act(() => result.current.setUsername('kyle_choy'))
    expect(result.current.username).toBe('kyle_choy')
    expect(localStorage.getItem('thenetwork.username')).toBe('kyle_choy')
  })

  it('restores the stored identity on mount (refresh simulation)', () => {
    localStorage.setItem('thenetwork.username', 'sam_indyk')
    const { result } = renderHook(() => useIdentity(), { wrapper: wrap })
    expect(result.current.username).toBe('sam_indyk')
  })

  it('rejects an invalid username silently (no state change, no write)', () => {
    const { result } = renderHook(() => useIdentity(), { wrapper: wrap })
    act(() => result.current.setUsername('bad name with spaces'))
    expect(result.current.username).toBeNull()
    expect(localStorage.getItem('thenetwork.username')).toBeNull()
  })

  it('clear() wipes localStorage and state', () => {
    const { result } = renderHook(() => useIdentity(), { wrapper: wrap })
    act(() => result.current.setUsername('kyle_choy'))
    act(() => result.current.clear())
    expect(result.current.username).toBeNull()
    expect(localStorage.getItem('thenetwork.username')).toBeNull()
  })

  it('throws when used outside the provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<TestConsumer />)).toThrow(/useIdentity must be used inside/)
    spy.mockRestore()
  })
})

function TestConsumer() {
  useIdentity()
  return null
}
