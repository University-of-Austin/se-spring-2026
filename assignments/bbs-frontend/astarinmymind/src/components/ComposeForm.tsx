// Textarea + post button. Phase 3 version — naive refetch after success, no
// optimistic update yet (that's Phase 4 where we use addOptimistic/removeOptimistic).
//
// Inputs:
//   onPosted: callback fired after a successful POST so the parent can refresh.
//
// Behavior:
//   - Submit disabled when message is empty, over 500 chars, or in flight.
//   - Char count flips red past the limit.
//   - Cmd+Enter / Ctrl+Enter posts.
//   - Server 422/4xx detail surfaces inline.

import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { useCurrentUser } from '../context/UserContext'
import { createPost } from '../api/posts'
import { ApiError } from '../api/client'

const MAX_LENGTH = 500

export function ComposeForm({ onPosted }: { onPosted: () => void }) {
  const { username } = useCurrentUser()
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const overLimit = message.length > MAX_LENGTH
  const isEmpty = message.trim().length === 0
  const canSubmit = !isEmpty && !overLimit && !submitting && !!username

  const submit = async () => {
    if (!canSubmit || !username) return
    setSubmitting(true)
    setError(null)
    try {
      await createPost(message, username)
      setMessage('')
      onPosted()
    } catch (err) {
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

  // If somehow rendered while signed out, render nothing.
  // Parent (FeedPage) shows a "sign in to post" prompt instead.
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
