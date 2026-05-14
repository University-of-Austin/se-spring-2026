// Reaction API. The frontend treats every reaction as a "heart" — we
// only ever post kind "heart" and only render the count of hearts.
// Backend supports arbitrary kind strings for future expansion.

import { apiRequest } from "./client";
import type { Reaction } from "../types";

export function listReactions(postId: number, signal?: AbortSignal): Promise<Reaction[]> {
  return apiRequest<Reaction[]>(`/posts/${postId}/reactions`, { signal });
}

export function createReaction(postId: number, username: string, kind = "heart"): Promise<Reaction> {
  return apiRequest<Reaction>(`/posts/${postId}/reactions`, {
    method: "POST",
    body: { username, kind },
  });
}

export function deleteReaction(postId: number, username: string): Promise<void> {
  return apiRequest<void>(`/posts/${postId}/reactions/${encodeURIComponent(username)}`, {
    method: "DELETE",
  });
}
