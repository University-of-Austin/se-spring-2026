/*
 * The API contract, mirrored from the A2 BBS server, as one source of truth.
 * Every field name and nullability here matches the server's response shapes
 * exactly (see assignments/bbs-webserver/cristpierce/main.py).
 */

export interface User {
  username: string
  created_at: string
  bio: string | null
  post_count: number
}

export interface Post {
  id: number
  username: string
  message: string
  created_at: string
  /** null until the post has been edited via PATCH /posts/{id}. */
  updated_at: string | null
}

export interface Reaction {
  post_id: number
  username: string
  kind: string
}

/** Query parameters accepted by GET /posts. */
export interface ListPostsParams {
  q?: string
  username?: string
  limit?: number
  offset?: number
}

/** The fixed palette of reaction emoji the UI offers. `kind` is free text on
 *  the server, but the client constrains it to a known, labelled set. */
export const REACTION_KINDS = ['👍', '❤️', '🎉', '😄'] as const
export type ReactionKind = (typeof REACTION_KINDS)[number]

export const REACTION_LABELS: Record<ReactionKind, string> = {
  '👍': 'thumbs up',
  '❤️': 'heart',
  '🎉': 'celebrate',
  '😄': 'laugh',
}

/** Constraints the server enforces — duplicated here so the UI can validate
 *  before sending and explain the rules to the user. */
export const LIMITS = {
  messageMax: 500,
  messageMin: 1,
  usernameMin: 3,
  usernameMax: 20,
  usernamePattern: /^[a-zA-Z0-9_]+$/,
  bioMax: 200,
} as const
