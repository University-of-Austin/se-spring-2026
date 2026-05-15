import { api } from '../api/endpoints';
import type { PostOut } from '../api/types';
import { useMutation } from './useMutation';

type Args = { message: string; username: string };

// No optimistic update for posting. The server has the canonical id and
// timestamp; faking those client-side and reconciling later just causes
// duplicate-during-the-race UX bugs that the optimistic-delete tombstones
// don't help with for this direction.
export function useCreatePost() {
  return useMutation<Args, PostOut>(({ message, username }) =>
    api.createPost(message, username),
  );
}
