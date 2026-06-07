// Single fetch wrapper. Every request in the app goes through here, so
// loading/error semantics, X-Username injection, and ApiError shape are all
// in one place.

const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  username?: string;
  signal?: AbortSignal;
};

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, username, signal } = opts;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (username) headers['X-Username'] = username;

  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  let bodyJson: unknown = null;
  try {
    bodyJson = await res.json();
  } catch {
    /* body wasn't JSON; bodyJson stays null */
  }

  if (!res.ok) {
    throw parseApiError(res.status, bodyJson);
  }

  return bodyJson as T;
}

// FastAPI returns two shapes under "detail":
//   - 422 validation:  detail = [{loc: [...], msg, type}, ...]
//   - 4xx HTTPException: detail = "string message"
// Branch on Array.isArray(body.detail) to handle both. fieldErrors is keyed
// by the field name (loc[1] for body fields), used by forms to surface
// inline errors via aria-describedby.
function parseApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;

    if (Array.isArray(detail)) {
      const fieldErrors: Record<string, string> = {};
      let firstMsg = '';
      for (const item of detail) {
        if (item && typeof item === 'object' && 'msg' in item) {
          const obj = item as { loc?: unknown[]; msg: unknown };
          const msg = String(obj.msg);
          const field =
            Array.isArray(obj.loc) && obj.loc.length >= 2 ? String(obj.loc[1]) : 'body';
          if (!(field in fieldErrors)) fieldErrors[field] = msg;
          if (!firstMsg) firstMsg = msg;
        }
      }
      return new ApiError(status, firstMsg || 'Validation failed', fieldErrors);
    }

    if (typeof detail === 'string') {
      return new ApiError(status, detail);
    }
  }
  return new ApiError(status, `Request failed (${status})`);
}

// Build a urlsafe base64 cursor matching the A2 server format:
//   base64.urlsafe_b64encode(json.dumps({"id": <int>}).encode())
// btoa produces standard base64; we swap +/ for -_ so the server's
// urlsafe_b64decode accepts it. Padding is preserved.
export function buildCursor(lastId: number): string {
  return btoa(JSON.stringify({ id: lastId }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

export { API_BASE };
