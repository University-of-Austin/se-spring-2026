// The single place in the app that calls window.fetch.
//
// Why funnel every request through here:
//   - one base-URL lookup (VITE_API_BASE)
//   - one X-Username injection rule
//   - one error-envelope shape, so views never see raw Response objects
//   - one place to add request logging / auth headers / retries later

const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

// A2 returns `{ "detail": "<string>" }` for every error code (400, 404,
// 409, 422).  That single-string `detail` is the only field we surface
// to the user, so the error type carries it explicitly alongside the
// HTTP status.  status === 0 means the fetch itself rejected — the
// network is down or CORS blocked the response before headers arrived.
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type FetchOpts = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  asUser?: string | null;   // sets X-Username for endpoints that need it
  signal?: AbortSignal;
};

export async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.asUser) headers["X-Username"] = opts.asUser;

  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
    });
  } catch (err) {
    // fetch() only rejects on network failures, not HTTP errors.
    // AbortError is re-thrown unchanged so useApi's cleanup logic
    // can recognise it and not write to state.
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "Cannot reach the server. Is the backend running on port 8000?");
  }

  // 204 No Content — DELETE /posts/{id} returns this.
  if (response.status === 204) return undefined as T;

  // Try to parse JSON whether the response is success or error.  A 422
  // from FastAPI still has a JSON body and we want its `detail`.
  let bodyJson: unknown = null;
  const text = await response.text();
  if (text.length > 0) {
    try {
      bodyJson = JSON.parse(text);
    } catch {
      // Non-JSON response — fall through with bodyJson = null.
    }
  }

  if (!response.ok) {
    const detail =
      typeof bodyJson === "object" && bodyJson !== null && "detail" in bodyJson
        ? String((bodyJson as { detail: unknown }).detail)
        : `HTTP ${response.status}`;
    throw new ApiError(response.status, detail);
  }

  return bodyJson as T;
}
