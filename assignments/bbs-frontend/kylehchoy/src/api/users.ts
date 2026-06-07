import { apiFetch } from './client'
import type { Post, User } from './types'

export function listUsers(limit = 100, offset = 0): Promise<User[]> {
  return apiFetch<User[]>(`/users?limit=${limit}&offset=${offset}`)
}

export function getUser(username: string): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(username)}`)
}

export function createUser(username: string): Promise<User> {
  return apiFetch<User>('/users', {
    method: 'POST',
    body: { username },
  })
}

export function getUserPosts(username: string, limit = 50, offset = 0): Promise<Post[]> {
  const enc = encodeURIComponent(username)
  return apiFetch<Post[]>(`/users/${enc}/posts?limit=${limit}&offset=${offset}`)
}

export function patchBio(username: string, bio: string | null): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(username)}`, {
    method: 'PATCH',
    body: { bio },
    requireAuth: true,
  })
}
