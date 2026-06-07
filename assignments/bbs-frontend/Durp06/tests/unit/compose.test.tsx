/**
 * ComposePage: client-side validation, char count behavior, Ctrl+Enter
 * submit, and server-422 surfacing. Tests use a stub `bbs` module that
 * resolves/rejects deterministically so the test isn't coupled to a real
 * backend.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { IdentityProvider } from '../../src/identity/IdentityContext';
import * as bbs from '../../src/api/bbs';
import ComposePage from '../../src/pages/ComposePage';

function setup() {
  localStorage.setItem('bbs:username', 'alice');
  return render(
    <MemoryRouter initialEntries={['/compose']}>
      <IdentityProvider>
        <ComposePage />
      </IdentityProvider>
    </MemoryRouter>,
  );
}

describe('ComposePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('disables the post button when the textarea is empty', () => {
    setup();
    const btn = screen.getByRole('button', { name: /post/i });
    expect(btn).toBeDisabled();
  });

  it('shows a character count and turns red past 500', async () => {
    const user = userEvent.setup();
    setup();
    const ta = screen.getByLabelText(/message/i);
    await user.type(ta, 'hello');
    expect(screen.getByText(/5\s*\/\s*500/)).toBeInTheDocument();

    // Fast-set a long value using fireEvent-style; userEvent.type is O(n).
    await user.clear(ta);
    await user.click(ta);
    // Set value directly via paste for speed
    await user.paste('x'.repeat(501));
    const counter = screen.getByText(/501\s*\/\s*500/);
    expect(counter).toHaveClass(/over/i);
  });

  it('submits via Ctrl+Enter and shows 422 server error inline', async () => {
    const user = userEvent.setup();
    const spy = vi
      .spyOn(bbs, 'createPost')
      .mockRejectedValueOnce(new bbs.ApiError(422, 'message too short'));
    setup();
    const ta = screen.getByLabelText(/message/i);
    await user.click(ta);
    await user.paste('hi');
    await user.keyboard('{Control>}{Enter}{/Control}');

    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    expect(spy).toHaveBeenCalledWith('alice', 'hi');
    expect(await screen.findByRole('alert')).toHaveTextContent(/message too short/i);
  });
});
