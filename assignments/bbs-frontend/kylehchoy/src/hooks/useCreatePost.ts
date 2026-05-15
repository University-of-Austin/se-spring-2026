import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPost, type CreatePostBody } from '../api/posts'
import type { ListPostsResponse, Post } from '../api/types'
import { useIdentity } from '../auth/IdentityContext'

interface Vars {
  body: CreatePostBody
  idempotencyKey?: string
}

interface RootCtx {
  prevPages: Array<[unknown, ListPostsResponse | undefined]>
  tempId: number
}

/**
 * Optimistic post-create mutation.
 *
 * onMutate:
 *   - Cancels any in-flight ['posts', ...] queries (so the optimistic
 *     write doesn't get clobbered by a late response).
 *   - Snapshots every ['posts', ...] cache shape and prepends a temp
 *     Post with id = -Date.now() (negative so it cannot collide with
 *     a real server id).
 *   - For replies (parent_id !== null), also touches ['post', parentId,
 *     'replies'] and ['post', parentId].
 * onError:
 *   - Restores every snapshotted query.
 * onSettled:
 *   - Invalidates ['posts'] and (if reply) ['post', parentId, ...] so
 *     the server's canonical version replaces the temp.
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

      // Snapshot + write to every ['posts', ...] cache.
      const prevPages: Array<[unknown, ListPostsResponse | undefined]> = []
      const caches = qc.getQueriesData<ListPostsResponse>({ queryKey })
      for (const [key, value] of caches) {
        prevPages.push([key, value])
        if (!value) continue
        // Only inject into the top-level feed (no filters). If a cached
        // query has a search term, skip — we don't know if our message
        // matches the FTS query.
        const k = key as unknown[]
        const params = (k[1] as { q?: string } | undefined) ?? {}
        if (params.q) continue
        qc.setQueryData<ListPostsResponse>(key as unknown[], {
          posts: [temp, ...value.posts],
          next_cursor: value.next_cursor,
        })
      }

      // For replies, also prepend to the parent's replies cache.
      if (body.parent_id != null) {
        const replyKey = ['post', body.parent_id, 'replies']
        await qc.cancelQueries({ queryKey: replyKey })
        const prev = qc.getQueryData<Post[]>(replyKey)
        if (prev) {
          qc.setQueryData<Post[]>(replyKey, [...prev, temp])
        }
      }

      return { prevPages, tempId }
    },

    onError: (_err, _vars, ctx) => {
      if (!ctx) return
      for (const [key, value] of ctx.prevPages) {
        qc.setQueryData(key as unknown[], value)
      }
    },

    onSettled: (_data, _err, vars) => {
      qc.invalidateQueries({ queryKey: ['posts'] })
      if (vars.body.parent_id != null) {
        qc.invalidateQueries({ queryKey: ['post', vars.body.parent_id, 'replies'] })
        qc.invalidateQueries({ queryKey: ['post', vars.body.parent_id] })
      }
    },
  })
}
