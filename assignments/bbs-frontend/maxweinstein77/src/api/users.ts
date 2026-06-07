// User-related API calls. Wraps the A2 endpoints behind typed functions.

import { apiRequest } from "./client";
import type { User } from "../types";

export function listUsers(): Promise<User[]> {
  return apiRequest<User[]>("/users");
}

export function getUser(username: string): Promise<User> {
  return apiRequest<User>(`/users/${encodeURIComponent(username)}`);
}

export function createUser(username: string): Promise<User> {
  return apiRequest<User>("/users", {
    method: "POST",
    body: { username },
  });
}
