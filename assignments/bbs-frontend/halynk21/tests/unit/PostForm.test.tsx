import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { ApiError } from '../../src/api/client';
import { PostForm } from '../../src/components/PostForm';
import { ToastProvider } from '../../src/context/ToastContext';
import { UserProvider } from '../../src/context/UserContext';

// Mock the endpoints module so PostForm calls our test double instead of
// the real backend. createPost rejects with a 422 ApiError carrying a
// fieldErrors.message — exactly what the server would return for a
// validation failure on the message field.
vi.mock('../../src/api/endpoints', () => ({
  api: {
    createPost: vi.fn(),
  },
}));

import { api } from '../../src/api/endpoints';

function renderPostForm() {
  return render(
    <MemoryRouter>
      <UserProvider>
        <ToastProvider>
          <PostForm />
        </ToastProvider>
      </UserProvider>
    </MemoryRouter>,
  );
}

describe('PostForm', () => {
  beforeEach(() => {
    localStorage.setItem('bbs:username', 'alice');
    vi.clearAllMocks();
  });

  test('disables submit when textarea is empty', () => {
    renderPostForm();
    const submit = screen.getByRole('button', { name: /post/i });
    expect(submit).toBeDisabled();
  });

  test('enables submit once user types non-empty content', () => {
    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i);
    fireEvent.change(textarea, { target: { value: 'hello world' } });
    const submit = screen.getByRole('button', { name: /post/i });
    expect(submit).toBeEnabled();
  });

  test('surfaces server 422 fieldErrors.message inline next to the textarea', async () => {
    vi.mocked(api.createPost).mockRejectedValueOnce(
      new ApiError(422, 'Validation', { message: 'Message must be at most 500 characters' }),
    );

    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i);
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: /post/i }));

    // Inline error appears, not just a toast — and it's tied to the
    // textarea via aria-describedby.
    const error = await screen.findByRole('alert');
    expect(error).toHaveTextContent(/at most 500/i);

    const errorId = error.getAttribute('id');
    expect(errorId).toBeTruthy();
    expect(textarea.getAttribute('aria-describedby')).toBe(errorId);
    expect(textarea.getAttribute('aria-invalid')).toBe('true');
  });

  test('Cmd+Enter inside textarea submits the form', async () => {
    vi.mocked(api.createPost).mockResolvedValueOnce({
      id: 1,
      username: 'alice',
      message: 'hello',
      created_at: new Date().toISOString(),
      updated_at: null,
    });

    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i);
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true });

    await waitFor(() => {
      expect(api.createPost).toHaveBeenCalledWith('hello', 'alice');
    });
  });

  test('clears the textarea after a successful post', async () => {
    vi.mocked(api.createPost).mockResolvedValueOnce({
      id: 2,
      username: 'alice',
      message: 'cleared after',
      created_at: new Date().toISOString(),
      updated_at: null,
    });

    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'cleared after' } });
    fireEvent.click(screen.getByRole('button', { name: /post/i }));

    await waitFor(() => {
      expect(textarea.value).toBe('');
    });
  });

  test('surfaces non-422 string-detail errors via error.message inline', async () => {
    // A2 returns 404 + {detail: "user not found"} when X-Username doesn't
    // match any user. ApiError parses the string detail into .message with
    // empty fieldErrors — so PostForm must fall back to .message, otherwise
    // the failure is silent (post just doesn't appear, no UI feedback).
    vi.mocked(api.createPost).mockRejectedValueOnce(
      new ApiError(404, 'user not found', {}),
    );

    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i);
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: /post/i }));

    const error = await screen.findByRole('alert');
    expect(error).toHaveTextContent(/user not found/i);
    expect(textarea.getAttribute('aria-invalid')).toBe('true');
  });

  test('clears stale server error as soon as the user resumes typing', async () => {
    vi.mocked(api.createPost).mockRejectedValueOnce(
      new ApiError(422, 'Validation', { message: 'Too long' }),
    );

    renderPostForm();
    const textarea = screen.getByLabelText(/new post/i);
    fireEvent.change(textarea, { target: { value: 'first try' } });
    fireEvent.click(screen.getByRole('button', { name: /post/i }));

    // Error appears
    await screen.findByRole('alert');

    // User edits — error should disappear immediately (not wait for next submit)
    fireEvent.change(textarea, { target: { value: 'first try!' } });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
