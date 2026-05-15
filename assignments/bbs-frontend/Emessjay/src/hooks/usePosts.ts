import { listPosts } from "../api/endpoints";
import { useApi } from "./useApi";

export function usePosts(params: { limit: number; offset: number; q: string }) {
  return useApi(
    (signal) => listPosts(params, signal),
    [params.limit, params.offset, params.q],
  );
}
