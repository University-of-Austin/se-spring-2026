/* Thin, typed wrappers around useResource for the single-GET views. */

import { api } from '../lib/api'
import { useResource } from './useResource'

export function useUsers() {
  return useResource((signal) => api.listUsers(signal), [])
}

export function useUser(username: string) {
  return useResource((signal) => api.getUser(username, signal), [username], {
    enabled: username.length > 0,
  })
}

export function useUserPosts(username: string) {
  return useResource((signal) => api.getUserPosts(username, signal), [username], {
    enabled: username.length > 0,
  })
}

export function usePost(id: number) {
  return useResource((signal) => api.getPost(id, signal), [id], {
    enabled: Number.isFinite(id) && id > 0,
  })
}
