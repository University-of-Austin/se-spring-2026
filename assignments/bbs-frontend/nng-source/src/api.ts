import { ApiError, type Board, type LoginResponse, type Post, type User } from "./types";

const BASE_URL = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
  username?: string | null;  // sent as X-Username
  query?: Record<string, string | number | undefined>;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token, username, query } = opts;

  let url = `${BASE_URL}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (username) headers["X-Username"] = username;

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError(
      "Could not reach the server. Is the backend running on " + BASE_URL + "?",
      0,
    );
  }

  if (res.status === 204) return undefined as T;

  let payload: unknown = null;
  const text = await res.text();
  if (text) {
    try { payload = JSON.parse(text); } catch { payload = text; }
  }

  if (!res.ok) {
    const detail = extractDetail(payload);
    throw new ApiError(detail || `${res.status} ${res.statusText}`, res.status);
  }

  return payload as T;
}

function extractDetail(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (payload && typeof payload === "object" && "detail" in payload) {
    const d = (payload as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      // FastAPI Pydantic 422: each entry has {msg, loc, type}
      return d
        .map((e) => {
          if (e && typeof e === "object" && "msg" in e) {
            return String((e as { msg: unknown }).msg);
          }
          return JSON.stringify(e);
        })
        .join("; ");
    }
  }
  return "";
}

/**
 * Resolve a backend-relative path (e.g. "/static/avatars/3.png") to a full URL.
 * Returns null unchanged so components can short-circuit cleanly.
 */
export function resolveBackendUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${BASE_URL}${path.startsWith("/") ? path : "/" + path}`;
}

// ------------------------ Endpoints --------------------------------------

export const api = {
  base: BASE_URL,

  // ---- auth ----
  signup: (username: string, password: string) =>
    request<User>("/users", { method: "POST", body: { username, password } }),

  login: (username: string, password: string) =>
    request<LoginResponse>("/login", { method: "POST", body: { username, password } }),

  logout: (token: string) =>
    request<void>("/logout", { method: "POST", token }),

  // ---- users ----
  listUsers: () => request<User[]>("/users"),
  getUser: (username: string) => request<User>(`/users/${encodeURIComponent(username)}`),
  patchBio: (username: string, bio: string, token: string) =>
    request<User>(`/users/${encodeURIComponent(username)}`, {
      method: "PATCH",
      body: { bio },
      token,
    }),
  getUserPosts: (username: string, opts?: { limit?: number; offset?: number }) =>
    request<Post[]>(`/users/${encodeURIComponent(username)}/posts`, { query: opts }),

  // ---- posts ----
  listPosts: (opts?: { q?: string; username?: string; board?: string; limit?: number; offset?: number }) =>
    request<Post[]>("/posts", { query: opts }),
  getPost: (id: number) => request<Post>(`/posts/${id}`),
  createPost: (
    message: string,
    username: string,
    token: string,
    board?: string,
  ) =>
    request<Post>("/posts", {
      method: "POST",
      body: { message, board },
      token,
      username,
    }),
  deletePost: (id: number, token: string) =>
    request<void>(`/posts/${id}`, { method: "DELETE", token }),

  // ---- avatars ----
  uploadAvatar: async (username: string, file: File, token: string): Promise<User> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${BASE_URL}/users/${encodeURIComponent(username)}/avatar`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      },
    );
    const text = await res.text();
    let payload: unknown = null;
    if (text) {
      try { payload = JSON.parse(text); } catch { payload = text; }
    }
    if (!res.ok) {
      throw new ApiError(extractDetail(payload) || `${res.status} ${res.statusText}`, res.status);
    }
    return payload as User;
  },

  deleteAvatar: (username: string, token: string) =>
    request<User>(`/users/${encodeURIComponent(username)}/avatar`, {
      method: "DELETE",
      token,
    }),

  // ---- boards ----
  listBoards: () => request<Board[]>("/boards"),
};
