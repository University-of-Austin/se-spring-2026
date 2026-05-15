/**
 * FeedPage: loading → success rendering and the optimistic-delete rollback
 * path. The contract: clicking delete removes the row immediately, and if
 * the server fails, the row is restored and an error toast/inline message
 * appears.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { IdentityProvider } from '../../src/identity/IdentityContext';
import { ToastProvider, ToastTray } from '../../src/hooks/useToast';
import * as bbs from '../../src/api/bbs';
import FeedPage from '../../src/pages/FeedPage';

const POSTS: bbs.Post[] = [
  {
    id: 1,
    username: 'alice',
    message: 'first',
    created_at: '2026-05-15T00:00:00Z',
    updated_at: '2026-05-15T00:00:00Z',
  },
  {
    id: 2,
    username: 'bob',
    message: 'second',
    created_at: '2026-05-15T00:00:01Z',
    updated_at: '2026-05-15T00:00:01Z',
  },
];

function renderFeed() {
  localStorage.setItem('bbs:username', 'alice');
  return render(
    <MemoryRouter initialEntries={['/']}>
      <IdentityProvider>
        <ToastProvider>
          <FeedPage />
          <ToastTray />
        </ToastProvider>
      </IdentityProvider>
    </MemoryRouter>,
  );
}

describe('FeedPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a loading state then the post list', async () => {
    vi.spyOn(bbs, 'listPosts').mockResolvedValueOnce({ posts: POSTS, nextCursor: null });
    renderFeed();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
    expect(await screen.findByText('first')).toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });

  it('optimistically removes a deleted post and rolls back on server failure', async () => {
    vi.spyOn(bbs, 'listPosts').mockResolvedValue({ posts: POSTS, nextCursor: null });

    // Hold the delete in flight so we can observe the optimistic-removed state
    // before the server resolves (or in this case, rejects).
    let rejectDelete: (err: unknown) => void = () => {};
    const deletePromise = new Promise<void>((_, reject) => {
      rejectDelete = reject;
    });
    const deleteSpy = vi.spyOn(bbs, 'deletePost').mockReturnValueOnce(deletePromise);

    const user = userEvent.setup();
    renderFeed();

    expect(await screen.findByText('first')).toBeInTheDocument();
    const deleteBtn = screen.getByRole('button', { name: /delete post 1/i });
    await user.click(deleteBtn);

    // Optimistic: row disappears while the delete is still in flight.
    await waitFor(() => expect(screen.queryByText('first')).not.toBeInTheDocument());
    expect(deleteSpy).toHaveBeenCalledWith(1);

    // Reject — rollback should restore the row and surface the error.
    rejectDelete(new bbs.ApiError(500, 'server boom'));

    expect(await screen.findByText('first')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent(/server boom/i);
  });
});
