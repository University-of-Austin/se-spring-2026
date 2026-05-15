import { ApiError, type ValidationDetail } from './types'

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  'http://localhost:8000'

/**
 * The single source of identity for fetch calls.
 * IdentityContext mounts the current username here so api/posts.ts and
 * api/users.ts don't need to thread it through every call signature.
 * setIdentity(null) clears it (e.g. after logout / switch user).
 */
let currentUsername: string | null = null
export function setIdentity(username: string | null): void {
  currentUsername = username
}
export function getIdentity(): string | null {
  return currentUsername
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'
  body?: unknown
  /** Sends X-Username from current identity. Throws if no identity. */
  requireAuth?: boolean
  /** Adds Idempotency-Key header (POST /posts only). */
  idempotencyKey?: string
  /** Adds If-None-Match (GET /posts/{id} only). */
  ifNoneMatch?: string
  /** Surface 304 as null instead of throwing. */
  allow304?: boolean
}

/**
 * Single fetch wrapper. All API calls go through here.
 *
 * - Joins path to VITE_API_BASE (defaults to http://localhost:8000).
 * - Injects X-Username from setIdentity() if requireAuth is true.
 * - Parses JSON on success.
 * - Normalizes errors into ApiError with a human-readable message.
 * - 304 returns null when allow304 is true; otherwise throws.
 */
export async function apiFetch<T = unknown>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (opts.requireAuth) {
    if (!currentUsername) {
      throw new ApiError(
        401,
        'No identity set',
        'You need to set an identity before doing that. Open Switch User.',
      )
    }
    headers['X-Username'] = currentUsername
  } else if (currentUsername) {
    // Optional auth: pass header when we have one. A2's GET /posts/{id}/reactions
    // returns user_reactions only when the header is present.
    headers['X-Username'] = currentUsername
  }

  if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey
  if (opts.ifNoneMatch) headers['If-None-Match'] = opts.ifNoneMatch

  const url = `${API_BASE}${path}`
  let res: Response
  try {
    res = await fetch(url, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    })
  } catch (err) {
    // Network error (server down, DNS, CORS preflight failure)
    throw new ApiError(
      0,
      String(err),
      'Could not reach the backend. Is it running on port 8000?',
    )
  }

  if (opts.allow304 && res.status === 304) {
    return null as T
  }

  if (res.status === 204) {
    return undefined as T
  }

  let payload: unknown = null
  const ct = res.headers.get('content-type') ?? ''
  if (ct.includes('application/json')) {
    payload = await res.json().catch(() => null)
  } else if (!res.ok) {
    payload = await res.text().catch(() => '')
  }

  if (!res.ok) {
    throw toApiError(res.status, payload)
  }

  return payload as T
}

function toApiError(status: number, payload: unknown): ApiError {
  const detail = extractDetail(payload)
  const message = humanize(status, detail)
  return new ApiError(status, detail, message)
}

function extractDetail(
  payload: unknown,
): string | ValidationDetail[] {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const d = (payload as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) return d as ValidationDetail[]
  }
  if (typeof payload === 'string') return payload
  return 'Request failed.'
}

function humanize(
  status: number,
  detail: string | ValidationDetail[],
): string {
  if (Array.isArray(detail)) {
    // First validation error, e.g. "body.message: String should have at most 500 characters"
    const first = detail[0]
    if (!first) return `Validation failed (${status}).`
    const loc = first.loc.filter((p) => p !== 'body').join('.')
    return loc ? `${loc}: ${first.msg}` : first.msg
  }
  if (status === 404) return detail || 'Not found.'
  if (status === 403) return detail || 'Forbidden.'
  if (status === 409) return detail || 'Conflict — that name is taken.'
  return detail || `Request failed (${status}).`
}

export { API_BASE }
