// Centralized fetch wrapper. Handles the three failure modes from lecture 5.2:
//   1. Network failure (fetch promise rejects)
//   2. HTTP error (response.ok === false) -- fetch does NOT throw on this
//   3. Bad JSON (response.json() throws SyntaxError)

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  username?: string | null;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.username) headers["X-Username"] = opts.username;

  const response = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });

  if (!response.ok) {
    // Try to surface the server's detail (A2 returns {detail: "..."} on 422 etc.)
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      // server didn't return JSON, that's fine
    }
    const message =
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `HTTP ${response.status}`);
    throw new ApiError(response.status, detail, message);
  }

  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}
