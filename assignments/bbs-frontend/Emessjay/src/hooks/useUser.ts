import { getUser, getUserPosts } from "../api/endpoints";
import { useApi } from "./useApi";

export function useUser(username: string) {
  return useApi((signal) => getUser(username, signal), [username]);
}

export function useUserPosts(username: string) {
  return useApi((signal) => getUserPosts(username, signal), [username]);
}
