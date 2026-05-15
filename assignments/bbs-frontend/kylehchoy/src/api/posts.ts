import { apiFetch, apiFetchWithMeta, type FetchResult } from './client'
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

export interface TrendingParams {
  window?: number
  limit?: number
}

/**
 * Shortcut for ?sort=top with sensible defaults (24h window, 10 items).
 * Equivalent to listPosts({ sort: 'top', window: 24, limit: 10 }) but
 * with a clearer call site for the sidebar widget.
 */
export function getTrending(params: TrendingParams = {}): Promise<Post[]> {
  const qs = buildQuery({ ...params } as Record<string, unknown>)
  return apiFetch<Post[]>(`/posts/trending${qs}`)
}

export function listPosts(params: ListPostsParams = {}): Promise<ListPostsResponse> {
  const qs = buildQuery(params as Record<string, unknown>)
  return apiFetch<ListPostsResponse>(`/posts${qs}`)
}

export function getPost(id: number): Promise<Post> {
  return apiFetch<Post>(`/posts/${id}`)
}

/**
 * Conditional GET against A2's weak ETag on /posts/{id}.
 * Pass the previously-seen ETag as ifNoneMatch; the server returns
 * 304 with no body when the post is unchanged. Caller keeps its
 * cached Post in that case.
 *
 * Caches ETags in a module-level Map so callers can use it as a
 * stateless function — first call carries no If-None-Match, subsequent
 * calls send the last-seen ETag automatically.
 */
const etagCache = new Map<number, string>()

/** Drop the cached ETag for a post; next fetch will be unconditional. */
export function invalidatePostEtag(id: number): void {
  etagCache.delete(id)
}

export async function getPostWithEtag(id: number): Promise<FetchResult<Post>> {
  const ifNoneMatch = etagCache.get(id)
  const result = await apiFetchWithMeta<Post>(`/posts/${id}`, {
    ifNoneMatch,
    allow304: true,
  })
  if (result.etag) etagCache.set(id, result.etag)
  return result
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

/**
 * Variant that surfaces Location + ETag from the 201 response.
 * Currently used internally; exposed in case the UI wants to navigate
 * to the created post via Location instead of guessing the path.
 */
export function createPostWithMeta(
  body: CreatePostBody,
  idempotencyKey?: string,
): Promise<FetchResult<Post>> {
  return apiFetchWithMeta<Post>('/posts', {
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
