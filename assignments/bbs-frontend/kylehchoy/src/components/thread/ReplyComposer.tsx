import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../../api/types'
import { useCreatePost } from '../../hooks/useCreatePost'
import { useIdentity } from '../../auth/IdentityContext'
import { MESSAGE_MAX, isValidMessage } from '../../lib/validation'

/**
 * Inline reply composer that slides in beneath a ReplyCard.
 * Smaller, denser than the top-of-Wall ComposeBox.
 */
export function ReplyComposer({
  parentId,
  onDone,
}: {
  parentId: number
  onDone?: () => void
}) {
  const { username } = useIdentity()
  const [text, setText] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const mut = useCreatePost()

  if (!username) {
    return (
      <div style={inlineMsg}>
        <Link to="/signup" style={{ color: 'var(--gold)' }}>
          Join the Network to reply →
        </Link>
      </div>
    )
  }

  const len = text.length
  const over = len > MESSAGE_MAX
  const disabled = !isValidMessage(text) || mut.isPending

  const submit = () => {
    setErr(null)
    mut.mutate(
      { body: { message: text, parent_id: parentId } },
      {
        onSuccess: () => {
          setText('')
          onDone?.()
        },
        onError: (e) => setErr(e instanceof ApiError ? e.message : String(e)),
      },
    )
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!disabled) submit()
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
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid var(--hairline)',
        animation: 'replyComposerIn 200ms ease-out',
      }}
      aria-label={`Reply to post ${parentId}`}
    >
      <style>{`
        @keyframes replyComposerIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <label
        htmlFor={`reply-${parentId}`}
        style={{
          display: 'block',
          fontFamily: 'var(--font-sans)',
          fontSize: 10,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 6,
        }}
      >
        Reply
      </label>

      <textarea
        id={`reply-${parentId}`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Add to the thread…"
        rows={2}
        style={{
          width: '100%',
          fontFamily: 'var(--font-serif)',
          fontSize: 15,
          lineHeight: 1.5,
          color: 'var(--black)',
          background: 'transparent',
          border: 'none',
          outline: 'none',
          resize: 'vertical',
          padding: 0,
        }}
        autoFocus
      />

      <div style={meta}>
        <span style={{ ...metaCount, color: over ? '#b34a3a' : 'var(--muted)' }}>
          {len} / {MESSAGE_MAX}
        </span>
        <span style={{ display: 'flex', gap: 12 }}>
          {onDone ? (
            <button type="button" onClick={onDone} style={cancelBtn}>
              Cancel
            </button>
          ) : null}
          <button
            type="submit"
            disabled={disabled}
            style={{
              ...submitBtn,
              background: disabled ? 'var(--hairline)' : 'var(--gold)',
              cursor: disabled ? 'not-allowed' : 'pointer',
            }}
          >
            {mut.isPending ? 'Replying…' : 'Reply'}
          </button>
        </span>
      </div>

      {err ? (
        <p role="alert" style={errStyle}>
          {err}
        </p>
      ) : null}
    </form>
  )
}

const inlineMsg: React.CSSProperties = {
  marginTop: 16,
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 14,
  color: 'var(--muted)',
}

const meta: React.CSSProperties = {
  marginTop: 10,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 16,
}

const metaCount: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.16em',
  textTransform: 'uppercase',
}

const submitBtn: React.CSSProperties = {
  color: 'var(--white)',
  border: 0,
  padding: '5px 14px',
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
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

const errStyle: React.CSSProperties = {
  marginTop: 8,
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: '#b34a3a',
}
