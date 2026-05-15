import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { PostCard } from '../../src/components/feed/PostCard'
import { IdentityProvider } from '../../src/auth/IdentityContext'
import type { Post } from '../../src/api/types'

const realPost: Post = {
  id: 42,
  username: 'kyle_choy',
  parent_id: null,
  message: 'Hayek on coercion versus persuasion.',
  created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  updated_at: null,
  reaction_counts: { like: 4, laugh: 0, heart: 2 },
}

const optimisticPost: Post = {
  ...realPost,
  id: -1,
  message: 'optimistic temp',
}

function renderCard(post: Post) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <IdentityProvider>
        <MemoryRouter>
          <PostCard post={post} isFirst />
        </MemoryRouter>
      </IdentityProvider>
    </QueryClientProvider>,
  )
}

describe('PostCard', () => {
  it('renders the body, the relative time, the username, and the open-thread link', () => {
    renderCard(realPost)
    expect(screen.getByText('Hayek on coercion versus persuasion.')).toBeInTheDocument()
    expect(screen.getByText(/3h ago/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '@kyle_choy' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open thread/i })).toHaveAttribute('href', '/posts/42')
  })

  it('renders the ReactionBar for real posts and skips it for optimistic posts', () => {
    renderCard(realPost)
    expect(screen.getByRole('button', { name: /Add like reaction/i })).toBeInTheDocument()
    // Counts show as part of the button text — `like` count is 4
    expect(screen.getByRole('button', { name: /Add like reaction/i }).textContent).toContain('4')
  })

  it('shows a "posting…" eyebrow + ReactionBar hidden on optimistic (negative id) posts', () => {
    renderCard(optimisticPost)
    expect(screen.getByText(/posting…/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add like reaction/i })).toBeNull()
  })
})
