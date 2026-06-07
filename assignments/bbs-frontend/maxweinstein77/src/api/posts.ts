// Post-related API calls.

import { apiRequest } from "./client";
import type { Post } from "../types";

interface ListPostsParams {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

export function listPosts(params: ListPostsParams = {}): Promise<Post[]> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.username) search.set("username", params.username);
  search.set("limit", String(params.limit ?? 20));
  search.set("offset", String(params.offset ?? 0));
  return apiRequest<Post[]>(`/posts?${search.toString()}`, { signal: params.signal });
}

export function getPost(postId: number): Promise<Post> {
  return apiRequest<Post>(`/posts/${postId}`);
}

export function getUserPosts(username: string): Promise<Post[]> {
  return apiRequest<Post[]>(`/users/${encodeURIComponent(username)}/posts`);
}

export function createPost(message: string, username: string): Promise<Post> {
  return apiRequest<Post>("/posts", {
    method: "POST",
    body: { message },
    username,
  });
}

export function deletePost(postId: number): Promise<void> {
  return apiRequest<void>(`/posts/${postId}`, { method: "DELETE" });
}
