import { useRef, useState, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../../api/types'
import { useCreatePost, newIdempotencyKey } from '../../hooks/useCreatePost'
import { useIdentity } from '../../auth/IdentityContext'
import { MESSAGE_MAX, isValidMessage } from '../../lib/validation'

/**
 * Compose to the Wall.
 *
 * - Placeholder: "Dare to think. Dare to post." (UATX voice, locked in DESIGN.md)
 * - Live char counter; turns red past 500.
 * - Disabled when empty or over limit.
 * - Cmd/Ctrl + Enter submits.
 * - 422 detail surfaces inline beneath the textarea.
 * - Identity check: if not logged in, replaces compose with a "Join the Network" link.
 *
 * Optimistic insertion arrives in Phase 5. For now: mutate, invalidate, clear.
 */
export function ComposeBox({ parentId }: { parentId?: number | null }) {
  const { username } = useIdentity()
  const [text, setText] = useState('')
  const [serverError, setServerError] = useState<string | null>(null)

  const mut = useCreatePost()
  // Idempotency key for the current compose-intent. Stays stable across
  // retry attempts of the same composition; rotates after a successful
  // post so the next compose gets a fresh key.
  const idemKeyRef = useRef<string>(newIdempotencyKey())
  const submit = () => {
    setServerError(null)
    mut.mutate(
      {
        body: { message: text, parent_id: parentId ?? null },
        idempotencyKey: idemKeyRef.current,
      },
      {
        onSuccess: () => {
          setText('')
          idemKeyRef.current = newIdempotencyKey()
        },
        onError: (err) => {
          setServerError(err instanceof ApiError ? err.message : String(err))
        },
      },
    )
  }

  // Clear stale server error when the user edits.
  useEffect(() => {
    if (serverError) setServerError(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  if (!username) {
    return (
      <div
        style={{
          padding: '20px 0 28px',
          marginBottom: 36,
          borderBottom: '1px solid var(--gold)',
        }}
      >
        <p style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--muted)' }}>
          You need a name in the directory to post.{' '}
          <Link to="/signup" style={{ color: 'var(--gold)' }}>
            Join the Network →
          </Link>
        </p>
      </div>
    )
  }

  const len = text.length
  const over = len > MESSAGE_MAX
  const disabled = !isValidMessage(text) || mut.isPending

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (disabled) return
    submit()
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !disabled) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      style={{
        paddingBottom: 28,
        marginBottom: 36,
        borderBottom: '1px solid var(--gold)',
      }}
      aria-label={parentId ? 'Reply to thread' : 'Post to the Wall'}
    >
      <label
        htmlFor={`compose-${parentId ?? 'root'}`}
        style={{
          display: 'block',
          fontFamily: 'var(--font-sans)',
          fontSize: 10,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 10,
        }}
      >
        {parentId ? 'Reply' : 'Compose'}
      </label>

      <textarea
        id={`compose-${parentId ?? 'root'}`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Dare to think. Dare to post."
        rows={3}
        style={{
          width: '100%',
          fontFamily: 'var(--font-serif)',
          fontSize: 17,
          lineHeight: 1.5,
          color: 'var(--black)',
          background: 'transparent',
          border: 'none',
          outline: 'none',
          resize: 'vertical',
          padding: 0,
        }}
        aria-invalid={over || !!serverError}
        aria-describedby={`compose-meta-${parentId ?? 'root'}`}
      />

      <div
        id={`compose-meta-${parentId ?? 'root'}`}
        style={{
          marginTop: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 16,
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 10,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: over ? '#b34a3a' : 'var(--muted)',
          }}
          aria-live="polite"
        >
          {len} / {MESSAGE_MAX} {over ? 'over limit' : ''}
        </span>
        <button
          type="submit"
          disabled={disabled}
          style={{
            background: disabled ? 'var(--hairline)' : 'var(--gold)',
            color: 'var(--white)',
            border: 0,
            padding: '7px 18px',
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          {mut.isPending ? 'Posting…' : 'Post'}
        </button>
      </div>

      {serverError ? (
        <p
          role="alert"
          style={{
            marginTop: 10,
            fontFamily: 'var(--font-serif)',
            fontStyle: 'italic',
            fontSize: 14,
            color: '#b34a3a',
          }}
        >
          {serverError}
        </p>
      ) : null}
    </form>
  )
}
