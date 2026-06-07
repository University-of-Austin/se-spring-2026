import { listUserPosts } from '../api/bbs';
import { useResource } from './useResource';
import type { Post } from '../api/types';

export function useUserPosts(username: string) {
  return useResource<Post[]>((signal) => listUserPosts(username, signal), [username]);
}
