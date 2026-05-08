// The one file in the app that calls fetch().
// Every hook or component that talks to the backend goes through `api(...)`.
// Centralizing this means: base URL is set once, X-Username is added consistently,
// errors are normalized to a single shape, and 204 responses don't crash on .json().

// VITE_API_BASE comes from environment. Defaults to local A2 backend.
const BASE_URL = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

// Custom error class. Throwing this lets hooks render `error.detail` directly
// without needing to inspect HTTP response objects everywhere.
export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
    this.name = 'ApiError'
  }
}

// Generic <T> = "the type of the response body the caller expects."
// e.g., api<Post[]>('/posts') returns Promise<Post[]>.
export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; username?: string | null } = {}
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options.username) headers['X-Username'] = options.username

  const res = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  // 4xx / 5xx — try to read the FastAPI {detail: ...} body, fall back to status text.
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // body wasn't JSON; keep the statusText fallback
    }
    throw new ApiError(res.status, detail)
  }

  // 204 No Content — DELETE returns this; calling .json() on it would throw.
  if (res.status === 204) return undefined as T

  return res.json()
}
