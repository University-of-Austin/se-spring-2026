import { request, type User, type Post } from "./client";

export function listUsers(signal?: AbortSignal): Promise<User[]> {
  return request<User[]>("/users", { signal });
}

export function getUser(username: string, signal?: AbortSignal): Promise<User> {
  return request<User>(`/users/${encodeURIComponent(username)}`, { signal });
}

export function getUserPosts(username: string, signal?: AbortSignal): Promise<Post[]> {
  return request<Post[]>(`/users/${encodeURIComponent(username)}/posts`, { signal });
}

export function createUser(username: string): Promise<User> {
  return request<User>("/users", { method: "POST", body: { username } });
}

export function patchUser(username: string, bio: string): Promise<User> {
  return request<User>(`/users/${encodeURIComponent(username)}`, {
    method: "PATCH",
    body: { bio },
  });
}
