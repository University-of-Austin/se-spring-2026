import { useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { REACTION_KINDS, REACTION_LABELS, type ReactionKind } from '../lib/types'
import { getReaction, setReaction } from '../lib/reactionStore'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import { Spinner } from './ui/Spinner'
import styles from './ReactionBar.module.css'

/*
 * Optimistic, single-choice reactions. The A2 schema's UNIQUE(post_id,username)
 * means a user holds at most one reaction per post, so switching kinds is
 * remove-then-add. We update the UI immediately and roll back with a toast if
 * the server rejects it; a stray 409 (server already had a reaction we didn't
 * know about) is reconciled by replacing it.
 */
export function ReactionBar({ postId }: { postId: number }) {
  const { username } = useIdentity()
  const toast = useToast()
  const [current, setCurrent] = useState<string | null>(() =>
    username ? getReaction(username, postId) : null,
  )
  const [pending, setPending] = useState<ReactionKind | null>(null)

  useEffect(() => {
    setCurrent(username ? getReaction(username, postId) : null)
  }, [username, postId])

  async function toggle(kind: ReactionKind) {
    if (!username) {
      toast.info('Choose a username first to react.')
      return
    }
    if (pending) return

    const prev = current
    const next = prev === kind ? null : kind
    setPending(kind)
    setCurrent(next) // optimistic

    // Track whether the server-side remove already committed. If it did and a
    // later step fails, the server now holds NO reaction — so we must roll the
    // UI back to null (not to `prev`), or client + localStorage would falsely
    // claim `prev` is still active and that lie would survive a refresh.
    let removedCommitted = false

    try {
      if (next === null) {
        try {
          await api.removeReaction(postId, username)
        } catch (e) {
          if (!(e instanceof ApiError && e.status === 404)) throw e
        }
        removedCommitted = true
      } else {
        if (prev) {
          try {
            await api.removeReaction(postId, username)
          } catch (e) {
            if (!(e instanceof ApiError && e.status === 404)) throw e
          }
          removedCommitted = true
        }
        try {
          await api.addReaction(postId, username, next)
        } catch (e) {
          if (e instanceof ApiError && e.status === 409) {
            await api.removeReaction(postId, username)
            await api.addReaction(postId, username, next)
          } else {
            throw e
          }
        }
      }
      setReaction(username, postId, next)
    } catch (e) {
      if (removedCommitted) {
        // The old reaction is already gone server-side; match that truth.
        setCurrent(null)
        setReaction(username, postId, null)
      } else {
        setCurrent(prev)
      }
      toast.error(e instanceof ApiError ? e.message : 'Could not save your reaction.')
    } finally {
      setPending(null)
    }
  }

  return (
    <div className={styles.bar} role="group" aria-label="React to this post">
      {REACTION_KINDS.map((kind) => {
        const active = current === kind
        const isPending = pending === kind
        return (
          <button
            key={kind}
            type="button"
            className={`${styles.react} ${active ? styles.active : ''}`}
            aria-pressed={active}
            aria-label={`${active ? 'Remove' : 'Add'} ${REACTION_LABELS[kind]} reaction`}
            disabled={pending !== null}
            onClick={() => toggle(kind)}
          >
            {isPending ? (
              <Spinner size={14} />
            ) : (
              <span className={styles.emoji} aria-hidden="true">
                {kind}
              </span>
            )}
          </button>
        )
      })}
      {current && <span className={styles.note}>You reacted</span>}
    </div>
  )
}
