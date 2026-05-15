import { getApiBase } from './config'

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

function summarizeBody(body: unknown): string {
  if (body === null || body === undefined) return ''
  if (typeof body === 'string') return body
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    return JSON.stringify((body as { detail: unknown }).detail)
  }
  try {
    return JSON.stringify(body)
  } catch {
    return 'Request failed'
  }
}

export type ApiRequestOptions = RequestInit & {
  /** When set, sends X-Username (required for POST /posts). */
  usernameHeader?: string
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const base = getApiBase()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`

  const { usernameHeader, ...fetchOptions } = options

  const headers = new Headers(fetchOptions.headers)
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }
  if (usernameHeader) {
    headers.set('X-Username', usernameHeader)
  }
  if (fetchOptions.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(url, { ...fetchOptions, headers })

  if (res.status === 204) {
    return undefined as T
  }

  const text = await res.text()
  let parsed: unknown = null
  if (text) {
    try {
      parsed = JSON.parse(text) as unknown
    } catch {
      parsed = text
    }
  }

  if (!res.ok) {
    const msg = summarizeBody(parsed) || res.statusText || 'Request failed'
    throw new ApiError(msg, res.status, parsed)
  }

  return parsed as T
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError
}
