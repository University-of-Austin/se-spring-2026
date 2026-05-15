import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patchPost } from '../../api/posts'
import type { Post } from '../../api/types'
import { ApiError } from '../../api/types'
import { MESSAGE_MAX, isValidMessage } from '../../lib/validation'

/**
 * Inline edit mode for a post. Replaces the body with a textarea
 * when active. PATCHes via A2's author-gated endpoint; on success
 * updates the ['post', id] cache directly so the new message + new
 * updated_at land in place without a refetch.
 */
export function PostEditor({
  post,
  onDone,
}: {
  post: Post
  onDone: () => void
}) {
  const qc = useQueryClient()
  const [text, setText] = useState(post.message)
  const [err, setErr] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => patchPost(post.id, text),
    onSuccess: (updated) => {
      qc.setQueryData<Post>(['post', post.id], updated)
      qc.invalidateQueries({ queryKey: ['posts'] })
      onDone()
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : String(e)),
  })

  const len = text.length
  const over = len > MESSAGE_MAX
  const empty = !isValidMessage(text)
  const unchanged = text === post.message
  const disabled = empty || over || unchanged || mut.isPending

  const submit = () => {
    if (disabled) return
    setErr(null)
    mut.mutate()
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit()
  }
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      submit()
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      onDone()
    }
  }

  return (
    <form onSubmit={onSubmit} aria-label="Edit post">
      <label htmlFor={`edit-${post.id}`} style={labelStyle}>
        Editing
      </label>
      <textarea
        id={`edit-${post.id}`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={4}
        autoFocus
        style={textareaStyle}
      />
      <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <span style={{ ...metaCount, color: over ? '#b34a3a' : 'var(--muted)' }}>
          {len} / {MESSAGE_MAX} {over ? 'over limit' : ''}
        </span>
        <span style={{ display: 'flex', gap: 12 }}>
          <button type="button" onClick={onDone} style={cancelBtn}>Cancel · Esc</button>
          <button
            type="submit"
            disabled={disabled}
            style={{
              ...saveBtn,
              background: disabled ? 'var(--hairline)' : 'var(--gold)',
              cursor: disabled ? 'not-allowed' : 'pointer',
            }}
          >
            {mut.isPending ? 'Saving…' : 'Save · ⌘↵'}
          </button>
        </span>
      </div>
      {err ? (
        <p role="alert" style={{ marginTop: 8, fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: 13, color: '#b34a3a' }}>
          {err}
        </p>
      ) : null}
    </form>
  )
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 6,
}
const textareaStyle: React.CSSProperties = {
  width: '100%',
  fontFamily: 'var(--font-serif)',
  fontSize: 18,
  lineHeight: 1.5,
  color: 'var(--black)',
  background: 'transparent',
  border: '1px solid var(--gold)',
  padding: '12px 14px',
  outline: 'none',
  resize: 'vertical',
}
const metaCount: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.16em',
  textTransform: 'uppercase',
}
const cancelBtn: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  background: 'transparent',
  border: 0,
  cursor: 'pointer',
}
const saveBtn: React.CSSProperties = {
  color: 'var(--white)',
  border: 0,
  padding: '6px 16px',
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
}
