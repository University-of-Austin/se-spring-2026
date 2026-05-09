// Optimistic post creation: the new post appears in the feed instantly,
// then reconciles when the server responds (or rolls back on failure).
//
// The fake post uses a NEGATIVE id (-Date.now()) so it never collides with
// real ids (which are positive). On success, the parent's refetch replaces
// the optimistic post with the server-confirmed one — usePosts' offset=0
// replace semantic does the cleanup automatically. On failure we explicitly
// removeOptimistic and restore the textarea so the user can edit/retry.
//
// Inputs:
//   onPosted          — fired after success so the parent can refetch
//   addOptimistic     — prepend a Post to the feed locally
//   removeOptimistic  — remove a Post from the feed by id

import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { useCurrentUser } from '../context/useCurrentUser'
import { createPost } from '../api/posts'
import { ApiError } from '../api/client'
import type { Post } from '../types'

const MAX_LENGTH = 500

export function ComposeForm({
  onPosted,
  addOptimistic,
  removeOptimistic,
}: {
  onPosted: () => void
  addOptimistic: (post: Post) => void
  removeOptimistic: (id: number) => void
}) {
  const { username } = useCurrentUser()
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const overLimit = message.length > MAX_LENGTH
  const isEmpty = message.trim().length === 0
  const canSubmit = !isEmpty && !overLimit && !submitting && !!username

  const submit = async () => {
    if (!canSubmit || !username) return

    // Snapshot the current message before clearing — used to restore on failure.
    const sent = message

    // Build the fake post. Negative id avoids any collision with real (positive) ids.
    const tempId = -Date.now()
    const tempPost: Post = {
      id: tempId,
      username,
      message: sent,
      created_at: new Date().toISOString(),
      updated_at: null,
    }

    addOptimistic(tempPost)
    setMessage('')
    setSubmitting(true)
    setError(null)

    try {
      await createPost(sent, username)
      // Success: tell the parent to refetch. The fresh fetch (with offset=0)
      // will REPLACE the local posts array, sweeping the fake post away and
      // showing the real one with a real id + server timestamp.
      onPosted()
    } catch (err) {
      // Failure: yank the fake, restore the textarea, show the inline error.
      removeOptimistic(tempId)
      setMessage(sent)
      setError(err instanceof ApiError ? err.detail : 'Failed to post')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit()
  }

  // Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux) submits.
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      submit()
    }
  }

  if (!username) return null

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor="compose-message" className="sr-only">
        Message
      </label>
      <textarea
        id="compose-message"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`What's on your mind, @${username}?`}
        rows={3}
        disabled={submitting}
        className="w-full rounded border border-border bg-bg px-3 py-2 text-text focus:border-accent focus:outline-none resize-none"
      />

      <div className="flex items-center justify-between text-sm">
        <span className={`font-mono ${overLimit ? 'text-error' : 'text-muted'}`}>
          {message.length}/{MAX_LENGTH}
        </span>
        <div className="flex items-center gap-3">
          <span className="text-muted hidden sm:inline">⌘+Enter to post</span>
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded bg-accent text-bg px-4 py-2 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? 'Posting…' : 'Post'}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-error">{error}</p>}
    </form>
  )
}
