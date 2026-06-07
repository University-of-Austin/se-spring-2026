import { apiFetch } from "./client";
import type { Post } from "./types";

export type PostListParams = {
  q?: string;
  limit?: number;
  offset?: number;
  username?: string;
};

function buildQuery(params: PostListParams): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function listPosts(params: PostListParams = {}): Promise<Post[]> {
  return apiFetch<Post[]>(`/posts${buildQuery(params)}`);
}

export function getPost(id: number | string): Promise<Post> {
  return apiFetch<Post>(`/posts/${id}`);
}

export function createPost(message: string, username: string): Promise<Post> {
  return apiFetch<Post>("/posts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Username": username,
    },
    body: JSON.stringify({ message }),
  });
}

export function deletePost(id: number): Promise<void> {
  return apiFetch<void>(`/posts/${id}`, { method: "DELETE" });
}

export function listUserPosts(
  username: string,
  params: PostListParams = {},
): Promise<Post[]> {
  return apiFetch<Post[]>(
    `/users/${encodeURIComponent(username)}/posts${buildQuery(params)}`,
  );
}
