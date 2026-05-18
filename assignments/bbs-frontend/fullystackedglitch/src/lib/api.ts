import type { Post, PostListQuery, User } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// FastAPI 422 bodies look like { detail: [{ loc, msg, type }, ...] } or { detail: "..." }.
// We surface the first useful string so views can render it inline without each
// caller re-parsing the shape.
function describeError(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0];
      if (first && typeof first === "object" && "msg" in first) {
        return String((first as { msg: unknown }).msg);
      }
    }
  }
  return `Request failed (${status})`;
}

type FetchOptions = {
  method?: string;
  body?: unknown;
  username?: string | null;
  signal?: AbortSignal;
};

async function request<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.username) headers["X-Username"] = opts.username;

  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });

  if (res.status === 204) return undefined as T;

  // The three failure modes: network (fetch throws), HTTP (handled by !res.ok
  // below), bad JSON (a 2xx response with a non-JSON body — e.g., a proxy
  // returning HTML). Wrap the parse so the bad-JSON case surfaces as an
  // ApiError with a human-readable message instead of a raw SyntaxError.
  const text = await res.text();
  let body: unknown = undefined;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw new ApiError(
        res.status,
        text,
        `Server returned non-JSON response (${res.status})`,
      );
    }
  }

  if (!res.ok) {
    throw new ApiError(
      res.status,
      (body as { detail?: unknown } | undefined)?.detail,
      describeError(res.status, body),
    );
  }
  return body as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === "" || v === null) continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length ? `?${parts.join("&")}` : "";
}

export const api = {
  listUsers: (signal?: AbortSignal) =>
    request<User[]>("/users", { signal }),

  getUser: (username: string, signal?: AbortSignal) =>
    request<User>(`/users/${encodeURIComponent(username)}`, { signal }),

  getUserPosts: (username: string, signal?: AbortSignal) =>
    request<Post[]>(`/users/${encodeURIComponent(username)}/posts`, { signal }),

  createUser: (username: string) =>
    request<User>("/users", { method: "POST", body: { username } }),

  patchUserBio: (username: string, bio: string, actor: string) =>
    request<User>(`/users/${encodeURIComponent(username)}`, {
      method: "PATCH",
      body: { bio },
      username: actor,
    }),

  listPosts: (params: PostListQuery = {}, signal?: AbortSignal) =>
    request<Post[]>(`/posts${qs(params)}`, { signal }),

  getPost: (id: number, signal?: AbortSignal) =>
    request<Post>(`/posts/${id}`, { signal }),

  createPost: (message: string, actor: string) =>
    request<Post>("/posts", {
      method: "POST",
      body: { message },
      username: actor,
    }),

  deletePost: (id: number) =>
    request<void>(`/posts/${id}`, { method: "DELETE" }),

  patchPost: (id: number, message: string, actor: string) =>
    request<Post>(`/posts/${id}`, {
      method: "PATCH",
      body: { message },
      username: actor,
    }),
};

export const API_BASE = BASE;
