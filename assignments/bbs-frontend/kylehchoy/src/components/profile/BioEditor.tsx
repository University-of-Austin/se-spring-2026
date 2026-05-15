import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patchBio } from '../../api/users'
import type { User } from '../../api/types'
import { ApiError } from '../../api/types'
import { BIO_MAX } from '../../lib/validation'

/**
 * Inline bio editor on the profile page. Visible only when the
 * viewer's identity matches the profile owner.
 */
export function BioEditor({ user }: { user: User }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(user.bio ?? '')
  const [err, setErr] = useState<string | null>(null)

  // Enter edit mode and seed the draft from the current bio at that
  // moment. Avoids a setState-in-effect for the same purpose.
  const beginEdit = () => {
    setDraft(user.bio ?? '')
    setErr(null)
    setEditing(true)
  }

  const mut = useMutation({
    mutationFn: () => patchBio(user.username, draft.trim() === '' ? null : draft),
    onSuccess: (updated) => {
      qc.setQueryData(['user', user.username], updated)
      qc.invalidateQueries({ queryKey: ['users'] })
      setEditing(false)
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : String(e)),
  })

  if (!editing) {
    return (
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        {user.bio ? (
          <p style={{ fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.5 }}>
            {user.bio}
          </p>
        ) : (
          <p style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: 15, color: 'var(--muted)' }}>
            No bio yet.
          </p>
        )}
        <button type="button" onClick={beginEdit} style={editBtn}>
          {user.bio ? 'Edit bio' : 'Add a bio'}
        </button>
      </div>
    )
  }

  const len = draft.length
  const over = len > BIO_MAX
  const disabled = over || mut.isPending

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (!disabled) {
          setErr(null)
          mut.mutate()
        }
      }}
      style={{ marginTop: 12 }}
    >
      <label htmlFor="bio-edit" style={labelStyle}>
        Bio
      </label>
      <textarea
        id="bio-edit"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={2}
        placeholder="One line about you."
        style={textareaStyle}
        autoFocus
      />
      <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <span style={{ ...metaCount, color: over ? '#b34a3a' : 'var(--muted)' }}>
          {len} / {BIO_MAX}
        </span>
        <span style={{ display: 'flex', gap: 12 }}>
          <button type="button" onClick={() => setEditing(false)} style={cancelBtn}>Cancel</button>
          <button
            type="submit"
            disabled={disabled}
            style={{
              ...submitBtn,
              background: disabled ? 'var(--hairline)' : 'var(--gold)',
              cursor: disabled ? 'not-allowed' : 'pointer',
            }}
          >
            {mut.isPending ? 'Saving…' : 'Save bio'}
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

const editBtn: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  background: 'transparent',
  border: '1px solid var(--gold)',
  padding: '4px 10px',
  cursor: 'pointer',
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
  fontSize: 16,
  lineHeight: 1.5,
  color: 'var(--black)',
  background: 'transparent',
  border: '1px solid var(--gold)',
  padding: '10px 12px',
  outline: 'none',
  resize: 'vertical',
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
