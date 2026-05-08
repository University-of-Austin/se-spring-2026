// Mutation functions — wrappers around `api()` for write operations.
// Plain async functions (not hooks) because the calling component owns
// its own `submitting` / `submitError` state locally; nothing here needs
// to live across renders.

import { api } from './client'
import type { User, Post } from '../types'

export const createPost = (message: string, username: string) =>
  api<Post>('/posts', { method: 'POST', body: { message }, username })

export const deletePost = (id: number, username: string) =>
  api<void>(`/posts/${id}`, { method: 'DELETE', username })

export const createUser = (username: string) =>
  api<User>('/users', { method: 'POST', body: { username } })
