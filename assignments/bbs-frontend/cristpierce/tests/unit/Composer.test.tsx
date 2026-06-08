import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Composer } from '../../src/components/Composer'
import { IdentityProvider } from '../../src/context/IdentityContext'
import { ApiError } from '../../src/lib/api'

function setup(onPost: (message: string) => Promise<void>) {
  // IdentityProvider seeds from localStorage, so this makes the form "logged in".
  localStorage.setItem('bbs:username', 'tester')
  return render(
    <MemoryRouter>
      <IdentityProvider>
        <Composer onPost={onPost} />
      </IdentityProvider>
    </MemoryRouter>,
  )
}

describe('Composer', () => {
  it('disables Post when empty and enables it once there is text', async () => {
    const user = userEvent.setup()
    setup(vi.fn(async () => {}))
    const button = screen.getByRole('button', { name: /post/i })
    expect(button).toBeDisabled()
    await user.type(screen.getByRole('textbox'), 'hello board')
    expect(button).toBeEnabled()
  })

  it('marks the field invalid and disables Post past 500 characters', async () => {
    const user = userEvent.setup()
    setup(vi.fn(async () => {}))
    const textarea = screen.getByRole('textbox')
    await user.click(textarea)
    await user.paste('x'.repeat(501))

    expect(screen.getByText('501/500')).toBeInTheDocument()
    expect(textarea).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('button', { name: /post/i })).toBeDisabled()
  })

  it('surfaces a server 422 inline instead of swallowing it', async () => {
    const user = userEvent.setup()
    const onPost = vi.fn(async () => {
      throw new ApiError({
        status: 422,
        message: 'Invalid',
        fieldErrors: { message: 'String should have at most 500 characters' },
      })
    })
    setup(onPost)

    await user.type(screen.getByRole('textbox'), 'hi there')
    await user.click(screen.getByRole('button', { name: /post/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/at most 500 characters/i)
  })
})
