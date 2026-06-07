import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPost, type CreatePostBody } from '../api/posts'
import type { ListPostsResponse, Post } from '../api/types'
import { useIdentity } from '../auth/useIdentity'

interface Vars {
  body: CreatePostBody
  /** Required. Caller generates once per compose-intent so retries of the
   *  same intent are exactly-once via A2's Idempotency-Key handling. */
  idempotencyKey: string
}

interface RootCtx {
  prevPages: Array<[unknown, ListPostsResponse | undefined]>
  prevReplies?: Post[] | undefined
}

/**
 * RFC-4122 v4 if available; padded fallback otherwise.
 * Exported so callers can pre-generate a key for the lifetime of a
 * compose UI and reuse it across retries.
 */
export function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * Optimistic post-create mutation.
 *
 * Idempotency contract (Gold #1 of A2's reliability primitives):
 *   The caller must pass `idempotencyKey` in vars. To make a single
 *   compose-intent exactly-once across user retries, allocate the key
 *   when the user begins composing and pass the same value on every
 *   submit attempt until success. On success, generate a new key for
 *   the next compose.
 *
 *   Same key + same body → A2 returns the original 201 row.
 *   Same key + different body → A2 returns 422 with "Idempotency-Key
 *   mismatch: body does not match original request" (surfaces inline
 *   via ApiError.message).
 *
 * Optimistic cache moves:
 *   - Cancels in-flight ['posts', ...] queries so a late server response
 *     can't clobber the optimistic write.
 *   - Snapshots every ['posts', ...] cache, prepends a temp Post with
 *     id = -Date.now() (negative IDs cannot collide with server IDs;
 *     PostCard renders id < 0 as dimmed + "posting…").
 *   - Skips caches whose key carries a search term (we can't predict
 *     whether the new message matches the FTS query).
 *   - For replies (parent_id != null), also patches ['post', parentId,
 *     'replies'].
 * onError restores snapshots. onSettled invalidates so the server's
 * canonical row replaces the temp.
 */
export function useCreatePost() {
  const { username } = useIdentity()
  const qc = useQueryClient()

  return useMutation<Post, Error, Vars, RootCtx>({
    mutationFn: ({ body, idempotencyKey }) => createPost(body, idempotencyKey),

    onMutate: async ({ body }) => {
      const queryKey = ['posts']
      await qc.cancelQueries({ queryKey })

      const tempId = -Date.now()
      const now = new Date().toISOString()
      const temp: Post = {
        id: tempId,
        username: username ?? 'me',
        parent_id: body.parent_id ?? null,
        message: body.message,
        created_at: now,
        updated_at: null,
        reaction_counts: { like: 0, laugh: 0, heart: 0 },
      }

      const prevPages: Array<[unknown, ListPostsResponse | undefined]> = []
      const caches = qc.getQueriesData<ListPostsResponse>({ queryKey })
      for (const [key, value] of caches) {
        prevPages.push([key, value])
        if (!value) continue
        const k = key as unknown[]
        const params =
          (k[1] as { q?: string; sort?: string; username?: string } | undefined) ?? {}
        // Skip caches where the optimistic post wouldn't actually belong:
        //  - FTS searches: bm25 ranking is opaque, we can't know if the
        //    new post matches the query without re-running it
        //  - Trending: a brand-new post has zero reactions, so it can't
        //    be on a popularity leaderboard
        //  - Other-user profile pages: ?username=other filters out this
        //    author, so injecting our temp post would briefly show on a
        //    profile the post doesn't belong to
        if (params.q) continue
        if (params.sort === 'top') continue
        if (params.username && params.username !== username) continue
        qc.setQueryData<ListPostsResponse>(key as unknown[], {
          posts: [temp, ...value.posts],
          next_cursor: value.next_cursor,
        })
      }

      let prevReplies: Post[] | undefined
      if (body.parent_id != null) {
        const replyKey = ['post', body.parent_id, 'replies']
        await qc.cancelQueries({ queryKey: replyKey })
        prevReplies = qc.getQueryData<Post[]>(replyKey)
        if (prevReplies) qc.setQueryData<Post[]>(replyKey, [...prevReplies, temp])
      }

      return { prevPages, prevReplies }
    },

    onError: (_err, vars, ctx) => {
      if (!ctx) return
      for (const [key, value] of ctx.prevPages) {
        qc.setQueryData(key as unknown[], value)
      }
      if (vars.body.parent_id != null) {
        qc.setQueryData(['post', vars.body.parent_id, 'replies'], ctx.prevReplies)
      }
    },

    onSettled: (_data, _err, vars) => {
      qc.invalidateQueries({ queryKey: ['posts'] })
      if (username) {
        qc.invalidateQueries({ queryKey: ['user', username] })
        qc.invalidateQueries({ queryKey: ['user', username, 'posts'] })
      }
      if (vars.body.parent_id != null) {
        qc.invalidateQueries({ queryKey: ['post', vars.body.parent_id, 'replies'] })
        qc.invalidateQueries({ queryKey: ['post', vars.body.parent_id] })
      }
    },
  })
}
