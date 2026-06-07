import { apiFetch } from "./client";
import type { Reaction } from "./types";

export function listReactions(postId: number): Promise<Reaction[]> {
  return apiFetch<Reaction[]>(`/posts/${postId}/reactions`);
}

export function addReaction(
  postId: number,
  username: string,
  kind: string,
): Promise<Reaction> {
  return apiFetch<Reaction>(`/posts/${postId}/reactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, kind }),
  });
}

export function removeReactions(postId: number, username: string): Promise<void> {
  return apiFetch<void>(
    `/posts/${postId}/reactions/${encodeURIComponent(username)}`,
    { method: "DELETE" },
  );
}
