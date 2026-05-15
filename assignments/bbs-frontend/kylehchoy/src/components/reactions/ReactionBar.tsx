import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getReactions } from '../../api/posts'
import { REACTION_KINDS, type Post, type ReactionKind } from '../../api/types'
import { useToggleReaction } from '../../hooks/useToggleReaction'
import { useIdentity } from '../../auth/useIdentity'

/**
 * Inline reaction strip on the post card / thread view.
 * Reads counts from the parent Post (always present); reads viewer state
 * from getReactions only when an identity is set (no point pinging the
 * server otherwise — A2 only returns user_reactions for known users).
 */
export function ReactionBar({ post }: { post: Post }) {
  const { username } = useIdentity()
  const toggle = useToggleReaction()
  // Per-bar pending tracking. Only the kind being mutated disables —
  // the other two stay clickable so the user can stack reactions.
  const [pendingKind, setPendingKind] = useState<ReactionKind | null>(null)

  const viewerQ = useQuery({
    queryKey: ['post', post.id, 'reactions'],
    queryFn: () => getReactions(post.id),
    enabled: !!username,
    staleTime: 30_000,
  })

  const viewerSet = new Set(viewerQ.data?.user_reactions ?? [])

  return (
    <div style={row} aria-label="Reactions">
      {REACTION_KINDS.map((kind) => {
        const reacted = viewerSet.has(kind)
        const count = post.reaction_counts[kind] ?? 0
        const isPending = pendingKind === kind
        return (
          <button
            key={kind}
            type="button"
            disabled={!username || isPending}
            onClick={() => {
              setPendingKind(kind)
              toggle.mutate(
                { postId: post.id, kind, reacted },
                { onSettled: () => setPendingKind(null) },
              )
            }}
            aria-pressed={reacted}
            aria-label={`${reacted ? 'Remove' : 'Add'} ${kind} reaction`}
            style={btn(reacted, !username)}
          >
            <span>{labelOf(kind)}</span>
            <span style={countStyle}>{count}</span>
          </button>
        )
      })}
    </div>
  )
}

function labelOf(k: ReactionKind): string {
  switch (k) {
    case 'like': return 'Like'
    case 'laugh': return 'Laugh'
    case 'heart': return 'Heart'
  }
}

const row: React.CSSProperties = {
  display: 'flex',
  gap: 18,
  marginTop: 16,
}

function btn(active: boolean, disabled: boolean): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'baseline',
    gap: 8,
    fontFamily: 'var(--font-sans)',
    fontSize: 10,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    color: active ? 'var(--gold)' : 'var(--muted)',
    background: 'transparent',
    border: 0,
    padding: 0,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  }
}

const countStyle: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  color: 'var(--black)',
  letterSpacing: '0.04em',
}
