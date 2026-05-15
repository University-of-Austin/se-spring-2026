import { useMutation, useQueryClient } from '@tanstack/react-query'
import { addReaction, removeReaction, getReactions } from '../api/posts'
import type {
  ListPostsResponse,
  Post,
  ReactionKind,
  ReactionsResponse,
} from '../api/types'

interface Vars {
  postId: number
  kind: ReactionKind
  /** Current viewer state — if true, we're removing; if false, adding. */
  reacted: boolean
}

interface Ctx {
  prev: ReactionsResponse | undefined
  prevPostCaches: Array<[unknown, ListPostsResponse | undefined]>
  prevReplyCaches: Array<[unknown, Post[] | undefined]>
}

/**
 * Optimistic toggle of one reaction kind on one post.
 * Updates three caches in lockstep:
 *   - ['post', id, 'reactions']  (canonical reaction state for that post)
 *   - ['posts', ...]              (every Wall cache: bumps counts on the matching post)
 *   - ['post', id, 'replies']    (reply lists; bumps counts on matching child)
 */
export function useToggleReaction() {
  const qc = useQueryClient()

  return useMutation<void, Error, Vars, Ctx>({
    mutationFn: ({ postId, kind, reacted }) =>
      reacted ? removeReaction(postId, kind) : addReaction(postId, kind),

    onMutate: async ({ postId, kind, reacted }) => {
      const delta = reacted ? -1 : +1
      const reactionsKey = ['post', postId, 'reactions']
      await qc.cancelQueries({ queryKey: reactionsKey })

      const prev = qc.getQueryData<ReactionsResponse>(reactionsKey)
      if (prev) {
        const nextCounts = { ...prev.counts, [kind]: Math.max(0, prev.counts[kind] + delta) }
        const nextViewer = (prev.user_reactions ?? []).filter((k) => k !== kind)
        if (!reacted) nextViewer.push(kind)
        qc.setQueryData<ReactionsResponse>(reactionsKey, {
          ...prev,
          counts: nextCounts,
          total: Math.max(0, prev.total + delta),
          user_reactions: nextViewer,
        })
      }

      // Patch every cached list that contains this post.
      const prevPostCaches = qc.getQueriesData<ListPostsResponse>({ queryKey: ['posts'] })
      for (const [key, value] of prevPostCaches) {
        if (!value) continue
        const idx = value.posts.findIndex((p) => p.id === postId)
        if (idx < 0) continue
        const next = { ...value }
        next.posts = [...value.posts]
        const p = next.posts[idx]
        next.posts[idx] = {
          ...p,
          reaction_counts: {
            ...p.reaction_counts,
            [kind]: Math.max(0, p.reaction_counts[kind] + delta),
          },
        }
        qc.setQueryData(key as unknown[], next)
      }

      const prevReplyCaches = qc.getQueriesData<Post[]>({
        predicate: (q) =>
          Array.isArray(q.queryKey) && q.queryKey[0] === 'post' && q.queryKey[2] === 'replies',
      })
      for (const [key, value] of prevReplyCaches) {
        if (!value) continue
        const idx = value.findIndex((p) => p.id === postId)
        if (idx < 0) continue
        const next = [...value]
        const p = next[idx]
        next[idx] = {
          ...p,
          reaction_counts: {
            ...p.reaction_counts,
            [kind]: Math.max(0, p.reaction_counts[kind] + delta),
          },
        }
        qc.setQueryData(key as unknown[], next)
      }

      return { prev, prevPostCaches, prevReplyCaches }
    },

    onError: (_err, _vars, ctx) => {
      if (!ctx) return
      if (ctx.prev !== undefined) {
        qc.setQueryData(['post', _vars.postId, 'reactions'], ctx.prev)
      }
      for (const [key, value] of ctx.prevPostCaches) qc.setQueryData(key as unknown[], value)
      for (const [key, value] of ctx.prevReplyCaches) qc.setQueryData(key as unknown[], value)
    },

    onSettled: (_data, _err, { postId }) => {
      qc.invalidateQueries({ queryKey: ['post', postId, 'reactions'] })
      // Don't invalidate ['posts'] — the optimistic counts on the feed are
      // already correct and we don't want to flash a re-fetch on every click.
    },
  })
}

/** Lightweight wrapper that fetches the canonical reactions for a post. */
export { getReactions }
