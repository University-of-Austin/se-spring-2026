import { apiFetch } from './client'
import type {
  ListPostsResponse,
  Post,
  ReactionKind,
  ReactionsResponse,
} from './types'

export interface ListPostsParams {
  q?: string
  username?: string
  limit?: number
  offset?: number
  cursor?: string
  sort?: 'recent' | 'top'
  window?: number
}

export function listPosts(params: ListPostsParams = {}): Promise<ListPostsResponse> {
  const qs = buildQuery(params as Record<string, unknown>)
  return apiFetch<ListPostsResponse>(`/posts${qs}`)
}

export function getPost(id: number): Promise<Post> {
  return apiFetch<Post>(`/posts/${id}`)
}

export interface CreatePostBody {
  message: string
  parent_id?: number | null
}

export function createPost(body: CreatePostBody, idempotencyKey?: string): Promise<Post> {
  return apiFetch<Post>('/posts', {
    method: 'POST',
    body,
    requireAuth: true,
    idempotencyKey,
  })
}

export function patchPost(id: number, message: string): Promise<Post> {
  return apiFetch<Post>(`/posts/${id}`, {
    method: 'PATCH',
    body: { message },
    requireAuth: true,
  })
}

export function deletePost(id: number): Promise<void> {
  return apiFetch<void>(`/posts/${id}`, {
    method: 'DELETE',
    requireAuth: true,
  })
}

export function listReplies(id: number, limit = 50, offset = 0): Promise<Post[]> {
  const qs = buildQuery({ limit, offset })
  return apiFetch<Post[]>(`/posts/${id}/replies${qs}`)
}

export function getReactions(postId: number): Promise<ReactionsResponse> {
  return apiFetch<ReactionsResponse>(`/posts/${postId}/reactions`)
}

export function addReaction(postId: number, kind: ReactionKind): Promise<void> {
  return apiFetch<void>(`/posts/${postId}/reactions/${kind}`, {
    method: 'PUT',
    requireAuth: true,
  })
}

export function removeReaction(postId: number, kind: ReactionKind): Promise<void> {
  return apiFetch<void>(`/posts/${postId}/reactions/${kind}`, {
    method: 'DELETE',
    requireAuth: true,
  })
}

function buildQuery(params: Record<string, unknown>): string {
  const entries: string[] = []
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    entries.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  }
  return entries.length ? `?${entries.join('&')}` : ''
}
