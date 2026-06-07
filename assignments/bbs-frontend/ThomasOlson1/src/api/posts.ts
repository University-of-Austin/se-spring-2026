import { request, type Post } from "./client";

export type ListPostsParams = {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
};

export function listPosts(params: ListPostsParams = {}, signal?: AbortSignal): Promise<Post[]> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  const suffix = qs.toString() ? `?${qs}` : "";
  return request<Post[]>(`/posts${suffix}`, { signal });
}

export function getPost(id: number, signal?: AbortSignal): Promise<Post> {
  return request<Post>(`/posts/${id}`, { signal });
}

export function createPost(message: string, username: string): Promise<Post> {
  return request<Post>("/posts", { method: "POST", body: { message }, username });
}

export function deletePost(id: number, username: string): Promise<void> {
  return request<void>(`/posts/${id}`, { method: "DELETE", username });
}

export function patchPost(id: number, message: string, username: string): Promise<Post> {
  return request<Post>(`/posts/${id}`, {
    method: "PATCH",
    body: { message },
    username,
  });
}
