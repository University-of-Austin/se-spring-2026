import { listPosts } from "../api/endpoints";
import { useApi } from "./useApi";
import { useOptimisticPosts } from "./useOptimisticPosts";

// feedVersion is bumped by OptimisticPostsProvider whenever a
// successful post completes; including it in deps refetches the
// feed automatically.

export function usePosts(params: { limit: number; offset: number; q: string }) {
  const { feedVersion } = useOptimisticPosts();
  return useApi(
    (signal) => listPosts(params, signal),
    [params.limit, params.offset, params.q, feedVersion],
  );
}
