import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ComposeBox } from '../../src/components/feed/ComposeBox'
import { IdentityProvider } from '../../src/auth/IdentityContext'

function renderCompose() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <IdentityProvider>
        <MemoryRouter>
          <ComposeBox />
        </MemoryRouter>
      </IdentityProvider>
    </QueryClientProvider>,
  )
}

describe('ComposeBox', () => {
  it('shows the "Join the Network" CTA when no identity is set', () => {
    renderCompose()
    expect(screen.getByText(/Join the Network/i)).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('renders the textarea + Post button when identity is set, with the locked placeholder', () => {
    localStorage.setItem('thenetwork.username', 'kyle_choy')
    renderCompose()
    const textarea = screen.getByLabelText(/^Compose/) as HTMLTextAreaElement
    expect(textarea).toBeInTheDocument()
    expect(textarea.placeholder).toBe('Dare to think. Dare to post.')
    expect(screen.getByRole('button', { name: /^post/i })).toBeDisabled()
  })

  it('keeps the submit disabled at length 0 and over 500 chars; live char count shows red when over', async () => {
    localStorage.setItem('thenetwork.username', 'kyle_choy')
    const u = userEvent.setup()
    renderCompose()
    const textarea = screen.getByLabelText(/^Compose/)
    const submit = screen.getByRole('button', { name: /^post/i })

    // Empty → disabled (NB: draft autosave restores from localStorage,
    // so make sure the input starts empty for this test).
    expect((textarea as HTMLTextAreaElement).value).toBe('')
    expect(submit).toBeDisabled()

    // 1 char → enabled
    await u.type(textarea, 'h')
    expect(submit).toBeEnabled()
    expect(screen.getByText('1 / 500')).toBeInTheDocument()

    // 501 chars → disabled again, count shown with "over limit"
    await u.clear(textarea)
    const overflow = 'x'.repeat(501)
    // userEvent's typing is slow at 500+; fire a single onChange via direct value set:
    ;(textarea as HTMLTextAreaElement).value = overflow
    textarea.dispatchEvent(new Event('input', { bubbles: true }))
    // RTL doesn't pick up the dispatched event for the controlled component the same way,
    // so as a fallback, repeat typing with a shorter sample of 510 chars in 2 chunks.
    if (!screen.queryByText(/over limit/i)) {
      await u.type(textarea, 'x'.repeat(510))
    }
    expect(screen.getByText(/over limit/i)).toBeInTheDocument()
    expect(submit).toBeDisabled()
  })

  it('Cmd+Enter on the textarea attempts to submit when valid', async () => {
    localStorage.setItem('thenetwork.username', 'kyle_choy')
    const u = userEvent.setup()
    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 1, username: 'kyle_choy', parent_id: null, message: 'hi', created_at: new Date().toISOString(), updated_at: null, reaction_counts: { like: 0, laugh: 0, heart: 0 } }), {
        status: 201,
        headers: { 'content-type': 'application/json' },
      }),
    )
    renderCompose()
    const textarea = screen.getByLabelText(/^Compose/)
    await u.type(textarea, 'hi')
    await u.keyboard('{Meta>}{Enter}{/Meta}')
    expect(fetchMock).toHaveBeenCalled()
    fetchMock.mockRestore()
  })
})
