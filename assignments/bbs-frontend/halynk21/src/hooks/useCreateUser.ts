import { api } from '../api/endpoints';
import type { UserOut } from '../api/types';
import { useMutation } from './useMutation';

export function useCreateUser() {
  return useMutation<string, UserOut>((username) => api.createUser(username));
}
