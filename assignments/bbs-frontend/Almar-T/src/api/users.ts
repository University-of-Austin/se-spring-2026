import { apiFetch } from "./client";
import type { User } from "./types";

export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>("/users");
}

export function getUser(username: string): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(username)}`);
}

export function createUser(username: string): Promise<User> {
  return apiFetch<User>("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
}
