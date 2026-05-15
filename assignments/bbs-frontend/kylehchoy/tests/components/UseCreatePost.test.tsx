import { describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { createPost } from '../../src/api/posts'
import type { Post } from '../../src/api/types'
import { IdentityProvider } from '../../src/auth/IdentityContext'
import { useCreatePost } from '../../src/hooks/useCreatePost'

vi.mock('../../src/api/posts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../src/api/posts')>()
  return {
    ...actual,
    createPost: vi.fn(),
  }
})

function makePost(id: number, message: string): Post {
  return {
    id,
    username: 'kyle_choy',
    parent_id: id === 1 ? null : 1,
    message,
    created_at: new Date('2026-05-15T00:00:00Z').toISOString(),
    updated_at: null,
    reaction_counts: { like: 0, laugh: 0, heart: 0 },
  }
}

describe('useCreatePost', () => {
  it('rolls back an optimistic reply when create fails', async () => {
    localStorage.setItem('thenetwork.username', 'kyle_choy')
    vi.mocked(createPost).mockRejectedValueOnce(new Error('nope'))

    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const replyKey = ['post', 1, 'replies']
    const existingReplies = [makePost(2, 'already here')]
    qc.setQueryData<Post[]>(replyKey, existingReplies)

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>
        <IdentityProvider>{children}</IdentityProvider>
      </QueryClientProvider>
    )

    const { result } = renderHook(() => useCreatePost(), { wrapper })

    await act(async () => {
      await expect(
        result.current.mutateAsync({
          body: { parent_id: 1, message: 'will fail' },
          idempotencyKey: 'reply-failure',
        }),
      ).rejects.toThrow('nope')
    })

    expect(qc.getQueryData(replyKey)).toEqual(existingReplies)
  })
})
