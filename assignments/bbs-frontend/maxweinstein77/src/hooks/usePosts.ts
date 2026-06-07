// React Query wrappers for post data + mutations.

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as postsApi from "../api/posts";
import type { Post } from "../types";

const PAGE_SIZE = 20;

// Paginated feed with infinite scroll. useInfiniteQuery handles accumulating
// pages and tracking whether there's another page to fetch.
// `signal` comes from React Query and is wired through to fetch so that
// when the search query changes (new query key), the in-flight request
// for the previous query gets aborted -- handles the "second-clicked
// button wins" race condition from lecture 5.2.
export function useFeed(searchQuery: string) {
  return useInfiniteQuery({
    queryKey: ["posts", { q: searchQuery }],
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      postsApi.listPosts({
        q: searchQuery || undefined,
        limit: PAGE_SIZE,
        offset: pageParam,
        signal,
      }),
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.length < PAGE_SIZE) return undefined; // exhausted
      return allPages.flat().length;
    },
  });
}

// Polled "what's the latest first page look like" query. Runs every 3s
// in the background. Compared against the displayed feed to drive the
// "N new posts" banner (gold pick #1). Polling at 3s comfortably meets
// the spec's "within ~5 seconds" target -- avg delay is ~1.5s.
export function useLatestPosts(searchQuery: string) {
  return useQuery({
    queryKey: ["posts-latest", { q: searchQuery }],
    queryFn: ({ signal }) =>
      postsApi.listPosts({ q: searchQuery || undefined, limit: 20, offset: 0, signal }),
    refetchInterval: 3000,
    refetchIntervalInBackground: false, // pause when tab is hidden
  });
}

export function usePost(postId: number | undefined) {
  return useQuery({
    queryKey: ["post", postId],
    queryFn: () => postsApi.getPost(postId!),
    enabled: postId !== undefined && !Number.isNaN(postId),
  });
}

export function useUserPosts(username: string | undefined) {
  return useQuery({
    queryKey: ["userPosts", username],
    queryFn: () => postsApi.getUserPosts(username!),
    enabled: !!username,
  });
}

// Optimistic create: the new post is inserted into the feed cache immediately
// with a temporary negative id, then reconciled when the server returns the
// real post. On failure, the optimistic post is removed and the snapshot
// restored. Pattern from React Query's useMutation.onMutate.
export function useCreatePost(username: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (message: string) => {
      if (!username) throw new Error("Choose a username first.");
      return postsApi.createPost(message, username);
    },
    onMutate: async (message) => {
      if (!username) return { snapshots: [] };
      await qc.cancelQueries({ queryKey: ["posts"] });
      const snapshots = qc.getQueriesData<{ pages: Post[][]; pageParams: unknown[] }>({
        queryKey: ["posts"],
      });
      // Insert a temp post with a negative id (real ids are positive).
      const tempPost: Post = {
        id: -Date.now(),
        username,
        message,
        created_at: new Date().toISOString(),
        updated_at: null,
      };
      qc.setQueriesData<{ pages: Post[][]; pageParams: unknown[] }>(
        { queryKey: ["posts"] },
        (old) => {
          if (!old || old.pages.length === 0) return old;
          const [first, ...rest] = old.pages;
          return { ...old, pages: [[tempPost, ...first], ...rest] };
        },
      );
      return { snapshots };
    },
    onError: (_err, _msg, context) => {
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["posts-latest"] });
      qc.invalidateQueries({ queryKey: ["userPosts", username] });
      qc.invalidateQueries({ queryKey: ["users"] }); // post_count changes
    },
  });
}

// Optimistic delete: the post disappears from every cached page immediately.
// On failure, the cached pages are restored from the snapshot.
export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: number) => postsApi.deletePost(postId),
    onMutate: async (postId) => {
      await qc.cancelQueries({ queryKey: ["posts"] });
      const snapshots = qc.getQueriesData<{ pages: Post[][]; pageParams: unknown[] }>({
        queryKey: ["posts"],
      });
      // Remove the post from every cached feed page.
      qc.setQueriesData<{ pages: Post[][]; pageParams: unknown[] }>(
        { queryKey: ["posts"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => page.filter((p) => p.id !== postId)),
          };
        },
      );
      return { snapshots };
    },
    onError: (_err, _postId, context) => {
      // Roll back to the snapshot if the server rejected the delete.
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["posts-latest"] });
      qc.invalidateQueries({ queryKey: ["userPosts"] });
    },
  });
}
