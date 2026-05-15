import { getUser } from '../api/bbs';
import { useResource } from './useResource';
import type { User } from '../api/types';

export function useUser(username: string) {
  return useResource<User>((signal) => getUser(username, signal), [username]);
}
