// Reactions per post. Same loading/error/data pattern as everything else.
// The toggle mutation is optimistic: the heart flips and count updates
// instantly, then reconciles with the server.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as reactionsApi from "../api/reactions";
import type { Reaction } from "../types";

export function useReactions(postId: number) {
  return useQuery({
    queryKey: ["reactions", postId],
    queryFn: ({ signal }) => reactionsApi.listReactions(postId, signal),
    enabled: postId > 0, // skip for optimistic temp posts (negative ids)
  });
}

// Toggle a heart reaction by the current user on/off on a post.
// Optimistic: the UI updates immediately, then rolls back on failure.
export function useToggleReaction(postId: number, username: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (currentlyReacted: boolean) => {
      if (!username) throw new Error("Choose a username to react.");
      if (currentlyReacted) {
        await reactionsApi.deleteReaction(postId, username);
      } else {
        await reactionsApi.createReaction(postId, username, "heart");
      }
    },
    onMutate: async (currentlyReacted) => {
      if (!username) return { snapshot: undefined };
      await qc.cancelQueries({ queryKey: ["reactions", postId] });
      const snapshot = qc.getQueryData<Reaction[]>(["reactions", postId]);
      qc.setQueryData<Reaction[]>(["reactions", postId], (old) => {
        const list = old ?? [];
        if (currentlyReacted) {
          return list.filter((r) => r.username !== username);
        }
        return [...list, { post_id: postId, username, kind: "heart" }];
      });
      return { snapshot };
    },
    onError: (_err, _vars, context) => {
      if (context?.snapshot !== undefined) {
        qc.setQueryData(["reactions", postId], context.snapshot);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["reactions", postId] });
    },
  });
}
