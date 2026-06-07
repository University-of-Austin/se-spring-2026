export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

const BASE_URL: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  username?: string | null;
  query?: Record<string, string | number | undefined | null>;
  signal?: AbortSignal;
}

// All HTTP traffic funnels through here so error-shape handling lives in one
// place. 422s (validation) and 4xx generally arrive with FastAPI's `detail`
// field — surfacing that as the error message is what makes the inline form
// errors readable to users.
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, username, query, signal } = opts;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (username) headers['X-Username'] = username;

  const url = new URL(path, BASE_URL);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
    }
  }

  let res: Response;
  try {
    res = await fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    // fetch throws on network failures (offline, DNS, CORS preflight reject).
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError(0, 'Network error — is the backend running?');
  }

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail = extractDetail(data) ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

function extractDetail(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // Pydantic 422 shape: list of {loc, msg, type}
    return detail
      .map((d: unknown) =>
        d && typeof d === 'object' && 'msg' in d
          ? String((d as { msg: unknown }).msg)
          : JSON.stringify(d),
      )
      .join('; ');
  }
  return null;
}
