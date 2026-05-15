import { getPost } from '../api/bbs';
import { useResource } from './useResource';
import type { Post } from '../api/types';

export function usePost(id: number) {
  return useResource<Post>((signal) => getPost(id, signal), [id]);
}
