import { request } from "./client";
import type { Post, PostsQuery } from "./types";

export function listPosts(query: PostsQuery = {}): Promise<Post[]> {
  return request<Post[]>("/posts", { query });
}

export function getPost(id: number): Promise<Post> {
  return request<Post>(`/posts/${id}`);
}

export function createPost(message: string, xUsername: string): Promise<Post> {
  return request<Post>("/posts", {
    method: "POST",
    body: { message },
    xUsername,
  });
}

export function updatePost(id: number, message: string, xUsername: string): Promise<Post> {
  return request<Post>(`/posts/${id}`, {
    method: "PATCH",
    body: { message },
    xUsername,
  });
}

export function deletePost(id: number): Promise<void> {
  return request<void>(`/posts/${id}`, { method: "DELETE" });
}
