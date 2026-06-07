// One typed function per backend endpoint the UI uses.
// Views and hooks call these — they never construct URLs themselves.

import { apiFetch } from "./client";
import type { PostOut, UserOut } from "./types";

// ─── Users ───────────────────────────────────────────────────────────

export function listUsers(signal?: AbortSignal): Promise<UserOut[]> {
  return apiFetch<UserOut[]>("/users", { signal });
}

export function getUser(username: string, signal?: AbortSignal): Promise<UserOut> {
  return apiFetch<UserOut>(`/users/${encodeURIComponent(username)}`, { signal });
}

export function createUser(username: string): Promise<UserOut> {
  return apiFetch<UserOut>("/users", {
    method: "POST",
    body: { username },
  });
}

export function getUserPosts(username: string, signal?: AbortSignal): Promise<PostOut[]> {
  return apiFetch<PostOut[]>(`/users/${encodeURIComponent(username)}/posts`, { signal });
}

// ─── Posts ───────────────────────────────────────────────────────────

export type ListPostsParams = {
  limit?: number;
  offset?: number;
  q?: string;
};

export function listPosts(params: ListPostsParams, signal?: AbortSignal): Promise<PostOut[]> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  if (params.q) search.set("q", params.q);
  const qs = search.toString();
  return apiFetch<PostOut[]>(qs ? `/posts?${qs}` : "/posts", { signal });
}

export function getPost(id: number, signal?: AbortSignal): Promise<PostOut> {
  return apiFetch<PostOut>(`/posts/${id}`, { signal });
}

export function createPost(message: string, asUser: string): Promise<PostOut> {
  return apiFetch<PostOut>("/posts", {
    method: "POST",
    body: { message },
    asUser,
  });
}

export function deletePost(id: number): Promise<void> {
  return apiFetch<void>(`/posts/${id}`, { method: "DELETE" });
}
