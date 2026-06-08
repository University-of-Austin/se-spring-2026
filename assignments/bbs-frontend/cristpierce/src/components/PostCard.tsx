import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Post } from '../lib/types'
import { LIMITS } from '../lib/types'
import { toApiError } from '../hooks/useResource'
import { renderMessage } from '../lib/mentions'
import { absoluteTime, relativeTime } from '../lib/time'
import { useIdentity } from '../context/IdentityContext'
import { UserBadge } from './UserBadge'
import { ReactionBar } from './ReactionBar'
import { Button } from './ui/Button'
import { ConfirmDialog } from './ui/ConfirmDialog'
import { CharCounter } from './CharCounter'
import { EditIcon, TrashIcon } from './ui/icons'
import { Spinner } from './ui/Spinner'
import styles from './PostCard.module.css'

interface PostCardProps {
  post: Post
  /** Parent owns list/cache state, so it performs the (optimistic) removal. */
  onDelete?: (post: Post) => void | Promise<void>
  /** Called with the server's updated post after a successful inline edit. */
  onUpdated?: (post: Post) => void
  /** True for an optimistic post still being confirmed by the server. */
  sending?: boolean
  showReactions?: boolean
}

export function PostCard({
  post,
  onDelete,
  onUpdated,
  sending = false,
  showReactions = true,
}: PostCardProps) {
  const { username } = useIdentity()
  const isAuthor = username === post.username

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(post.message)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const editErrorId = useId()

  async function confirmDelete() {
    setDeleting(true)
    try {
      await onDelete?.(post)
      setConfirmOpen(false)
    } finally {
      setDeleting(false)
    }
  }

  async function saveEdit() {
    const trimmed = draft.trim()
    if (!username || trimmed.length < LIMITS.messageMin || trimmed.length > LIMITS.messageMax) return
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await api.updatePost(post.id, username, trimmed)
      onUpdated?.(updated)
      setEditing(false)
    } catch (err) {
      const apiErr = toApiError(err)
      setSaveError(apiErr.fieldErrors?.message ?? apiErr.message)
    } finally {
      setSaving(false)
    }
  }

  const edited = post.updated_at !== null && post.updated_at !== undefined

  return (
    <article className={`${styles.card} ${sending ? styles.sending : ''}`}>
      <header className={styles.head}>
        {/* Avatar + name link to the profile. */}
        <UserBadge username={post.username} size={38} />

        <div className={styles.headRight}>
          {sending ? (
            <span className={styles.time}>
              <Spinner size={12} /> posting…
            </span>
          ) : (
            // Timestamp is the post permalink (kept a sibling of the avatar
            // link, never nested inside the message — which itself contains
            // @mention links).
            <Link
              to={`/posts/${post.id}`}
              className={styles.time}
              title={absoluteTime(post.created_at)}
            >
              {edited && <span className={styles.edited}>edited · </span>}
              {relativeTime(post.created_at)}
            </Link>
          )}

          {!sending && (
            <div className={styles.actions}>
              {isAuthor && !editing && (
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  aria-label="Edit post"
                  onClick={() => {
                    setDraft(post.message)
                    setSaveError(null)
                    setEditing(true)
                  }}
                >
                  <EditIcon size={16} />
                </Button>
              )}
              {onDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  aria-label="Delete post"
                  onClick={() => setConfirmOpen(true)}
                >
                  <TrashIcon size={16} />
                </Button>
              )}
            </div>
          )}
        </div>
      </header>

      {editing ? (
        <div className={styles.editArea}>
          <label htmlFor={`edit-${post.id}`} className="visually-hidden">
            Edit your post
          </label>
          <textarea
            id={`edit-${post.id}`}
            className={styles.editInput}
            value={draft}
            rows={3}
            autoFocus
            aria-invalid={draft.length > LIMITS.messageMax || saveError !== null}
            aria-describedby={saveError ? editErrorId : undefined}
            onChange={(e) => {
              setDraft(e.target.value)
              setSaveError(null)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setEditing(false)
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                e.preventDefault()
                saveEdit()
              }
            }}
          />
          {saveError && (
            <p id={editErrorId} className={styles.editError} role="alert">
              {saveError}
            </p>
          )}
          <div className={styles.editFooter}>
            <CharCounter value={draft.length} max={LIMITS.messageMax} />
            <div className={styles.editButtons}>
              <Button variant="ghost" size="sm" onClick={() => setEditing(false)} disabled={saving}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={saving}
                disabled={
                  draft.trim().length < LIMITS.messageMin ||
                  draft.length > LIMITS.messageMax ||
                  draft.trim() === post.message
                }
                onClick={saveEdit}
              >
                Save
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <p className={styles.message}>{renderMessage(post.message)}</p>
      )}

      {!editing && showReactions && !sending && (
        <footer className={styles.foot}>
          <ReactionBar postId={post.id} />
        </footer>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="Delete this post?"
        message="This permanently removes the post and its reactions. This can’t be undone."
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </article>
  )
}
