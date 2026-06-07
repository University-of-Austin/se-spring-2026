import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/bbs', () => ({
  bbsApi: {
    createPost: vi.fn(),
  },
}))

vi.mock('../hooks/useUsername', () => ({
  useUsername: () => ({
    username: 'alice',
    setUsername: vi.fn(),
    clearUsername: vi.fn(),
  }),
}))

import { FeedOptimisticProvider } from '../context/FeedOptimisticContext'
import { bbsApi } from '../api/bbs'
import { ComposePage } from './ComposePage'

function renderCompose() {
  return render(
    <BrowserRouter>
      <FeedOptimisticProvider>
        <ComposePage />
      </FeedOptimisticProvider>
    </BrowserRouter>,
  )
}

describe('ComposePage', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.mocked(bbsApi.createPost).mockReset()
  })

  it('disables submit when the message is empty (form validation)', () => {
    renderCompose()
    const submit = screen.getByRole('button', { name: /^post$/i })
    expect(submit).toBeDisabled()
  })

  it('shows loading state while the post request is in flight', async () => {
    const user = userEvent.setup()
    let resolvePost!: (value: {
      id: number
      username: string
      message: string
      created_at: string
    }) => void
    const pending = new Promise<{
      id: number
      username: string
      message: string
      created_at: string
    }>((res) => {
      resolvePost = res
    })
    vi.mocked(bbsApi.createPost).mockReturnValue(pending)

    renderCompose()
    await user.type(screen.getByLabelText(/message/i), 'hello from test')
    await user.click(screen.getByRole('button', { name: /^post$/i }))

    expect(screen.getByRole('status')).toHaveTextContent(/posting your message/i)
    resolvePost({
      id: 99,
      username: 'alice',
      message: 'hello from test',
      created_at: '2026-01-01T00:00:00Z',
    })
    await waitFor(() => {
      expect(screen.getByText(/message posted/i)).toBeInTheDocument()
    })
  })

  it('shows an inline error when the server rejects the post', async () => {
    const user = userEvent.setup()
    vi.mocked(bbsApi.createPost).mockRejectedValue(new Error('Server exploded'))

    renderCompose()
    await user.type(screen.getByLabelText(/message/i), 'valid body here')
    await user.click(screen.getByRole('button', { name: /^post$/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server exploded')
    })
  })
})
