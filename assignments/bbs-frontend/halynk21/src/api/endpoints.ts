// Typed wrappers for every A2 endpoint we use. Pages and hooks should call
// these — never `request()` directly — so the route shapes live in one file.

import { request } from './client';
import type { UserOut, PostOut, CursorPage } from './types';

type Opts = { signal?: AbortSignal; username?: string };

export const api = {
  // ── Users ────────────────────────────────────────────────────────────────
  createUser: (username: string, opts: Opts = {}) =>
    request<UserOut>('/users', { method: 'POST', body: { username }, ...opts }),

  listUsers: (opts: Opts = {}) =>
    request<UserOut[]>('/users', opts),

  getUser: (username: string, opts: Opts = {}) =>
    request<UserOut>(`/users/${encodeURIComponent(username)}`, opts),

  getUserPosts: (username: string, opts: Opts = {}) =>
    request<PostOut[]>(`/users/${encodeURIComponent(username)}/posts`, opts),

  // ── Posts ────────────────────────────────────────────────────────────────
  // Without ?cursor, the server returns a bare PostOut[] (newest first).
  // Used for the initial feed load and every poll tick.
  listRecent: (
    params: { q?: string; limit?: number },
    opts: Opts = {},
  ) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.limit !== undefined) qs.set('limit', String(params.limit));
    const tail = qs.toString();
    return request<PostOut[]>(`/posts${tail ? '?' + tail : ''}`, opts);
  },

  // With ?cursor, the server returns CursorPage and walks backward in id.
  // Used for "load more" — cursor is built by the caller from
  // min(loadedPosts.id) via buildCursor() in client.ts.
  listPage: (
    params: { q?: string; limit?: number; cursor: string },
    opts: Opts = {},
  ) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.limit !== undefined) qs.set('limit', String(params.limit));
    qs.set('cursor', params.cursor);
    return request<CursorPage>(`/posts?${qs.toString()}`, opts);
  },

  getPost: (id: number, opts: Opts = {}) =>
    request<PostOut>(`/posts/${id}`, opts),

  createPost: (message: string, username: string, opts: Opts = {}) =>
    request<PostOut>('/posts', { method: 'POST', body: { message }, username, ...opts }),

  // A2 spec: DELETE requires no X-Username — anyone can delete (matches
  // bronze "delete button visible to anyone" line). 204 on success.
  deletePost: (id: number, opts: Opts = {}) =>
    request<void>(`/posts/${id}`, { method: 'DELETE', ...opts }),
};
