/*
 * The API client — the ONLY place in the app that calls fetch().
 *
 * Responsibilities:
 *   - resolve the base URL from VITE_API_BASE (default http://localhost:8000)
 *   - inject Content-Type and the X-Username "identity" header
 *   - enforce a request timeout (so a dead backend surfaces as an error, not a
 *     spinner that hangs forever)
 *   - normalize EVERY failure into a single ApiError type, collapsing FastAPI's
 *     two different `detail` shapes (a string for HTTPException, an array of
 *     {loc,msg,type} for 422 validation) into one human message plus optional
 *     per-field errors for inline form display.
 *
 * Components never see a raw Response or a raw fetch rejection; they see typed
 * data or an ApiError. That is the contract the hooks layer is built on.
 */

import type { ListPostsParams, Post, Reaction, User } from './types'

export const API_BASE = (
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'
).replace(/\/+$/, '')

const DEFAULT_TIMEOUT_MS = 12_000

/** A single, uniform error type for the whole app. */
export class ApiError extends Error {
  /** HTTP status, or 0 for network/timeout failures. */
  readonly status: number
  /** Per-field messages keyed by field name, parsed from 422 responses. */
  readonly fieldErrors?: Record<string, string>
  /** True when the request never reached the server (offline / CORS / timeout). */
  readonly isNetwork: boolean
  /** True specifically when the client-side timeout fired. */
  readonly isTimeout: boolean

  constructor(opts: {
    status: number
    message: string
    fieldErrors?: Record<string, string>
    isNetwork?: boolean
    isTimeout?: boolean
  }) {
    super(opts.message)
    this.name = 'ApiError'
    this.status = opts.status
    this.fieldErrors = opts.fieldErrors
    this.isNetwork = opts.isNetwork ?? false
    this.isTimeout = opts.isTimeout ?? false
  }
}

interface FastApiValidationItem {
  loc: (string | number)[]
  msg: string
  type: string
}

/** Collapse a parsed error body into a message + optional field errors. */
export function normalizeErrorBody(
  status: number,
  body: unknown,
): { message: string; fieldErrors?: Record<string, string> } {
  const detail =
    body && typeof body === 'object' && 'detail' in body
      ? (body as { detail: unknown }).detail
      : undefined

  // 422 validation: detail is an array of {loc, msg, type}.
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {}
    const messages: string[] = []
    for (const raw of detail as FastApiValidationItem[]) {
      if (!raw || typeof raw.msg !== 'string') continue
      const loc = Array.isArray(raw.loc) ? raw.loc : []
      // Skip the leading scope segment ("body" / "query" / "path").
      const field = loc.length > 1 ? String(loc[loc.length - 1]) : String(loc[0] ?? '')
      const msg = raw.msg.replace(/^Value error,\s*/i, '')
      if (field) fieldErrors[field] = msg
      messages.push(msg)
    }
    return {
      message: messages[0] ?? defaultMessageForStatus(status),
      fieldErrors: Object.keys(fieldErrors).length ? fieldErrors : undefined,
    }
  }

  // HTTPException: detail is a plain string.
  if (typeof detail === 'string' && detail.trim()) {
    return { message: detail }
  }

  return { message: defaultMessageForStatus(status) }
}

function defaultMessageForStatus(status: number): string {
  switch (status) {
    case 400:
      return 'The request was missing something the server needs.'
    case 401:
    case 403:
      return 'You are not allowed to do that.'
    case 404:
      return 'Not found.'
    case 409:
      return 'That already exists.'
    case 422:
      return 'Some of that input was not valid.'
    case 429:
      return 'Too many requests — slow down a moment.'
    default:
      return status >= 500
        ? 'The server hit an error. Try again in a moment.'
        : `Request failed (${status}).`
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  /** Sent as the X-Username identity header (A2's honor-system auth). */
  username?: string
  signal?: AbortSignal
  timeoutMs?: number
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, username, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = opts

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (username) headers['X-Username'] = username

  // Combine an internal timeout with any caller-provided abort signal.
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (err) {
    clearTimeout(timer)
    if (timedOut) {
      throw new ApiError({
        status: 0,
        message: 'The server took too long to respond. Is the backend running?',
        isNetwork: true,
        isTimeout: true,
      })
    }
    // External cancellation (component unmounted / new search typed): re-throw
    // the DOMException so callers can ignore it rather than show an error.
    if (signal?.aborted) throw err
    throw new ApiError({
      status: 0,
      message:
        'Could not reach the server. Check that the backend is running and CORS is enabled.',
      isNetwork: true,
    })
  } finally {
    clearTimeout(timer)
  }

  if (res.status === 204) return undefined as T

  let parsed: unknown = undefined
  const text = await res.text()
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = text
    }
  }

  if (!res.ok) {
    const { message, fieldErrors } = normalizeErrorBody(res.status, parsed)
    throw new ApiError({ status: res.status, message, fieldErrors })
  }

  return parsed as T
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const usp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue
    usp.set(key, String(value))
  }
  const s = usp.toString()
  return s ? `?${s}` : ''
}

const enc = encodeURIComponent

/** The typed surface the rest of the app imports. */
export const api = {
  // ---- Users ----
  listUsers: (signal?: AbortSignal) => request<User[]>('/users', { signal }),

  getUser: (username: string, signal?: AbortSignal) =>
    request<User>(`/users/${enc(username)}`, { signal }),

  createUser: (username: string) =>
    request<User>('/users', { method: 'POST', body: { username } }),

  getUserPosts: (username: string, signal?: AbortSignal) =>
    request<Post[]>(`/users/${enc(username)}/posts`, { signal }),

  updateBio: (username: string, bio: string) =>
    request<User>(`/users/${enc(username)}`, { method: 'PATCH', body: { bio } }),

  // ---- Posts ----
  listPosts: (params: ListPostsParams = {}, signal?: AbortSignal) =>
    request<Post[]>(`/posts${buildQuery({ ...params })}`, { signal }),

  getPost: (id: number, signal?: AbortSignal) =>
    request<Post>(`/posts/${id}`, { signal }),

  createPost: (username: string, message: string) =>
    request<Post>('/posts', { method: 'POST', username, body: { message } }),

  updatePost: (id: number, username: string, message: string) =>
    request<Post>(`/posts/${id}`, { method: 'PATCH', username, body: { message } }),

  deletePost: (id: number) => request<void>(`/posts/${id}`, { method: 'DELETE' }),

  // ---- Feed (used for live polling: delta fetch of posts newer than `since`) ----
  feedSince: (since: string | undefined, limit: number, signal?: AbortSignal) =>
    request<Post[]>(`/feed${buildQuery({ since, limit })}`, { signal }),

  // ---- Reactions (the invented gold feature is built on these) ----
  addReaction: (postId: number, username: string, kind: string) =>
    request<Reaction>(`/posts/${postId}/reactions`, {
      method: 'POST',
      body: { username, kind },
    }),

  removeReaction: (postId: number, username: string) =>
    request<void>(`/posts/${postId}/reactions/${enc(username)}`, { method: 'DELETE' }),
}

export type Api = typeof api
