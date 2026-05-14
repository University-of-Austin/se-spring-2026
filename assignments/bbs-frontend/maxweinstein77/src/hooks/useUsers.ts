// React Query wrappers for user data.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: usersApi.listUsers,
  });
}

export function useUser(username: string | undefined) {
  return useQuery({
    queryKey: ["user", username],
    queryFn: () => usersApi.getUser(username!),
    enabled: !!username,
  });
}

// Lookup that returns null instead of throwing on 404. Used by Sign In
// to decide "new user" vs "returning user" without surfacing the 404
// as an error message.
export function useUserLookup() {
  const qc = useQueryClient();
  return async (username: string) => {
    try {
      const user = await qc.fetchQuery({
        queryKey: ["user", username],
        queryFn: () => usersApi.getUser(username),
      });
      return user;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  };
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: usersApi.createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
