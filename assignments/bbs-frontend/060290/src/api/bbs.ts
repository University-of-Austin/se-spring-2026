import { apiRequest } from './client'
import type { Post, User } from '../types/bbs'

export type ListPostsParams = {
  q?: string
  limit?: number
  offset?: number
}

export const bbsApi = {
  listPosts(params?: ListPostsParams): Promise<Post[]> {
    const search = new URLSearchParams()
    if (params?.q) {
      search.set('q', params.q)
    }
    if (params?.limit !== undefined) {
      search.set('limit', String(params.limit))
    }
    if (params?.offset !== undefined) {
      search.set('offset', String(params.offset))
    }
    const qs = search.toString()
    return apiRequest<Post[]>(`/posts${qs ? `?${qs}` : ''}`)
  },

  getPost(postId: number): Promise<Post> {
    return apiRequest<Post>(`/posts/${postId}`)
  },

  deletePost(postId: number): Promise<void> {
    return apiRequest<void>(`/posts/${postId}`, { method: 'DELETE' })
  },

  createPost(username: string, message: string): Promise<Post> {
    return apiRequest<Post>('/posts', {
      method: 'POST',
      body: JSON.stringify({ message }),
      usernameHeader: username,
    })
  },

  listUsers(): Promise<User[]> {
    return apiRequest<User[]>('/users')
  },

  createUser(username: string): Promise<User> {
    return apiRequest<User>('/users', {
      method: 'POST',
      body: JSON.stringify({ username }),
    })
  },

  getUser(username: string): Promise<User> {
    return apiRequest<User>(`/users/${encodeURIComponent(username)}`)
  },

  getUserPosts(username: string): Promise<Post[]> {
    return apiRequest<Post[]>(
      `/users/${encodeURIComponent(username)}/posts`,
    )
  },
}
