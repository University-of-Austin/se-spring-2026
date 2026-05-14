import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/api/client";
import type { ApiError, Post } from "@/api/types";

export type ThreadResponse = { posts: Post[] };

export function usePost(idStr: string) {
  const id = Number(idStr);
  const [thread, setThread] = useState<Post[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ThreadResponse>(`/posts/${id}/thread`);
      setThread(data.posts);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const deletePost = useCallback(
    async (targetId: number) => {
      await apiFetch(`/posts/${targetId}`, { method: "DELETE" });
      await refetch();
    },
    [refetch],
  );

  const reply = useCallback(
    async (message: string, parent_id: number) => {
      await apiFetch("/posts", { method: "POST", body: JSON.stringify({ message, parent_id }) });
      await refetch();
    },
    [refetch],
  );

  return { thread, loading, error, refetch, deletePost, reply };
}
