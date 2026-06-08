import { describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useResource } from '../../src/hooks/useResource'
import { ApiError } from '../../src/lib/api'

describe('useResource', () => {
  it('transitions loading -> success and exposes data', async () => {
    const { result } = renderHook(() => useResource(async () => 42, []))
    expect(result.current.status).toBe('loading')
    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.data).toBe(42)
    expect(result.current.error).toBeUndefined()
  })

  it('transitions loading -> error and keeps the ApiError', async () => {
    const { result } = renderHook(() =>
      useResource(async () => {
        throw new ApiError({ status: 500, message: 'boom' })
      }, []),
    )
    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error?.message).toBe('boom')
    expect(result.current.error?.status).toBe(500)
  })

  it('stays idle and never fetches when disabled', () => {
    const fetcher = vi.fn(async () => 1)
    const { result } = renderHook(() => useResource(fetcher, [], { enabled: false }))
    expect(result.current.status).toBe('idle')
    expect(fetcher).not.toHaveBeenCalled()
  })

  it('setData overwrites the cache for optimistic updates', async () => {
    const { result } = renderHook(() => useResource(async () => [1, 2], []))
    await waitFor(() => expect(result.current.status).toBe('success'))
    act(() => result.current.setData((prev) => [...(prev ?? []), 3]))
    expect(result.current.data).toEqual([1, 2, 3])
  })
})
