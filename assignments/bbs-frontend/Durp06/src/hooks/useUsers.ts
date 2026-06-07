import { listUsers } from '../api/bbs';
import { useResource } from './useResource';
import type { User } from '../api/types';

export function useUsers() {
  return useResource<User[]>((signal) => listUsers(signal), []);
}
