import { request } from "./client";
import type { Post, User } from "./types";

export function listUsers(): Promise<User[]> {
  return request<User[]>("/users");
}

export function getUser(username: string): Promise<User> {
  return request<User>(`/users/${encodeURIComponent(username)}`);
}

export function createUser(username: string, bio?: string): Promise<User> {
  return request<User>("/users", {
    method: "POST",
    body: bio !== undefined ? { username, bio } : { username },
  });
}

export function updateUserBio(username: string, bio: string, xUsername: string): Promise<User> {
  return request<User>(`/users/${encodeURIComponent(username)}`, {
    method: "PATCH",
    body: { bio },
    xUsername,
  });
}

export function listUserPosts(username: string): Promise<Post[]> {
  return request<Post[]>(`/users/${encodeURIComponent(username)}/posts`);
}
