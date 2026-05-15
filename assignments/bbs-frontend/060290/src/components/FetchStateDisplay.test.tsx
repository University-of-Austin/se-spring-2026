import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FetchStateDisplay } from './FetchStateDisplay'

describe('FetchStateDisplay', () => {
  it('shows a loading indicator while loading', () => {
    render(
      <FetchStateDisplay state={{ phase: 'loading' }}>
        {() => <p>Never</p>}
      </FetchStateDisplay>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Loading…')
  })

  it('shows a visible error message and retry when the request failed', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(
      <FetchStateDisplay
        state={{
          phase: 'error',
          message: 'Network down',
          httpStatus: 503,
        }}
        onRetry={onRetry}
      >
        {() => <p>Never</p>}
      </FetchStateDisplay>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Network down')
    await user.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
