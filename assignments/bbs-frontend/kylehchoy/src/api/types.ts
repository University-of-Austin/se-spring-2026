/**
 * TypeScript mirror of the A2 contract.
 * If this drifts from assignments/bbs-webserver/kylehchoy/models.py,
 * fix this file. The server is source of truth.
 */

export interface Post {
  id: number
  username: string
  parent_id: number | null
  message: string
  created_at: string
  updated_at: string | null
  reaction_counts: ReactionCounts
  /** FTS-only — present on GET /posts?q= hits, absent everywhere else. */
  snippet?: string
}

export interface ReactionCounts {
  like: number
  laugh: number
  heart: number
}

export type ReactionKind = keyof ReactionCounts

export const REACTION_KINDS: ReactionKind[] = ['like', 'laugh', 'heart']

export interface ListPostsResponse {
  posts: Post[]
  next_cursor: string | null
}

export interface User {
  username: string
  created_at: string
  bio: string | null
  post_count: number
}

export interface ReactionsResponse {
  counts: ReactionCounts
  total: number
  /** Only present when X-Username header is sent and user exists. */
  user_reactions?: ReactionKind[]
}

export interface ValidationDetail {
  type: string
  loc: (string | number)[]
  msg: string
  input?: unknown
}

/**
 * Normalized error shape used everywhere in the app.
 * Constructed in api/client.ts from raw fetch responses.
 */
export class ApiError extends Error {
  status: number
  detail: string | ValidationDetail[]
  /** Pre-formatted human-readable message for direct UI display. */
  override message: string

  constructor(status: number, detail: string | ValidationDetail[], message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.message = message
  }

  /** True when this is a Pydantic validation error from the server. */
  get isValidation(): boolean {
    return this.status === 422 && Array.isArray(this.detail)
  }

  /** First field-level error for a given form field, if any. */
  fieldError(field: string): string | null {
    if (!Array.isArray(this.detail)) return null
    const hit = this.detail.find((d) => d.loc.includes(field))
    return hit?.msg ?? null
  }
}
