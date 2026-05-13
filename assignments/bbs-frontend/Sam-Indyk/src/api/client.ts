import type { Post, PostsQuery, User } from "./types";

export const API_BASE: string =
  (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env
    .VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | undefined;
  readonly body: unknown;

  constructor(status: number, detail: string | undefined, body: unknown) {
    super(detail ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, signal } = opts;
  const finalHeaders: Record<string, string> = { ...headers };
  if (body !== undefined) finalHeaders["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: finalHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (e) {
    // Network-level failure (server down, DNS, offline).
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "Could not reach the server. Is the backend running?", e);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  let parsed: unknown = null;
  const text = await res.text();
  if (text.length > 0) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const detail = extractDetail(parsed) ?? res.statusText;
    throw new ApiError(res.status, detail, parsed);
  }

  return parsed as T;
}

function extractDetail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      // FastAPI 422 validation errors look like:
      //   [{loc, msg, type, ...}, ...]
      const parts = d
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            const msg = (entry as { msg: unknown }).msg;
            return typeof msg === "string" ? msg : null;
          }
          return null;
        })
        .filter((s): s is string => s !== null);
      if (parts.length > 0) return parts.join("; ");
    }
  }
  return undefined;
}

// ---- Endpoint helpers --------------------------------------------------

export const api = {
  // Users
  listUsers: (signal?: AbortSignal) => request<User[]>("/users", { signal }),
  getUser: (username: string, signal?: AbortSignal) =>
    request<User>(`/users/${encodeURIComponent(username)}`, { signal }),
  getUserPosts: (username: string, signal?: AbortSignal) =>
    request<Post[]>(`/users/${encodeURIComponent(username)}/posts`, { signal }),
  createUser: (username: string) =>
    request<User>("/users", { method: "POST", body: { username } }),

  // Posts
  listPosts: (query: PostsQuery = {}, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (query.q) params.set("q", query.q);
    if (query.username) params.set("username", query.username);
    if (query.limit !== undefined) params.set("limit", String(query.limit));
    if (query.offset !== undefined) params.set("offset", String(query.offset));
    const qs = params.toString();
    return request<Post[]>(`/posts${qs ? `?${qs}` : ""}`, { signal });
  },
  getPost: (id: number, signal?: AbortSignal) =>
    request<Post>(`/posts/${id}`, { signal }),
  createPost: (message: string, username: string) =>
    request<Post>("/posts", {
      method: "POST",
      body: { message },
      headers: { "X-Username": username },
    }),
  deletePost: (id: number) =>
    request<void>(`/posts/${id}`, { method: "DELETE" }),
};
