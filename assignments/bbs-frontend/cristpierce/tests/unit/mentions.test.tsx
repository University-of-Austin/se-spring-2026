import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { renderMessage } from '../../src/lib/mentions'

function renderMessageInRouter(message: string) {
  return render(<MemoryRouter>{renderMessage(message)}</MemoryRouter>)
}

describe('renderMessage', () => {
  it('linkifies @mentions to profile routes', () => {
    renderMessageInRouter('hi @alice and @bob_99')
    expect(screen.getByRole('link', { name: '@alice' })).toHaveAttribute('href', '/users/alice')
    expect(screen.getByRole('link', { name: '@bob_99' })).toHaveAttribute(
      'href',
      '/users/bob_99',
    )
  })

  it('does not linkify an @ mid-word (e.g. emails)', () => {
    renderMessageInRouter('reach me at bob@example')
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('leaves plain messages as text', () => {
    const { container } = renderMessageInRouter('just a normal post')
    expect(container.textContent).toContain('just a normal post')
    expect(screen.queryByRole('link')).toBeNull()
  })
})
