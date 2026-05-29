import { getPost } from "../api/endpoints";
import { useApi } from "./useApi";

export function usePost(id: number) {
  return useApi((signal) => getPost(id, signal), [id]);
}
