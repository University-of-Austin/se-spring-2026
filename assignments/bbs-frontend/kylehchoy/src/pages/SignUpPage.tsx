import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import { createUser, listUsers } from '../api/users'
import { ApiError } from '../api/types'
import { useIdentity } from '../auth/useIdentity'
import { USERNAME_MAX, USERNAME_MIN, isValidUsername } from '../lib/validation'
import { ErrorBanner } from '../components/states/States'

/**
 * Two affordances on one page: register a new name, or switch to an
 * existing one. Per A2: X-Username is preference, not auth — there's
 * no password. The UI surfaces this honestly with the language
 * "claim a name" / "switch identity".
 */
export default function SignUpPage() {
  const { username: current, setUsername } = useIdentity()
  const qc = useQueryClient()
  const navigate = useNavigate()

  const [newName, setNewName] = useState('')
  const [serverError, setServerError] = useState<string | null>(null)

  const usersQ = useQuery({ queryKey: ['users'], queryFn: () => listUsers(200, 0) })

  const createMut = useMutation({
    mutationFn: (name: string) => createUser(name),
    onSuccess: (u) => {
      setUsername(u.username)
      qc.invalidateQueries({ queryKey: ['users'] })
      navigate('/', { replace: true })
    },
    onError: (err) => {
      setServerError(err instanceof ApiError ? err.message : String(err))
    },
  })

  const onCreate = (e: FormEvent) => {
    e.preventDefault()
    setServerError(null)
    if (!isValidUsername(newName)) return
    createMut.mutate(newName)
  }

  const onSwitch = (name: string) => {
    setUsername(name)
    navigate('/', { replace: true })
  }

  const valid = isValidUsername(newName)
  const showInlineRule = newName.length > 0 && !valid

  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px 56px' }}>
      <header style={{ marginBottom: 32, paddingBottom: 14, borderBottom: '2px solid var(--black)' }}>
        <p style={eyebrow}>Register · or switch identity</p>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 500, lineHeight: 1.1 }}>
          Join the Network.
        </h1>
        <p style={{ marginTop: 12, fontFamily: 'var(--font-serif)', fontSize: 15, lineHeight: 1.55, color: 'var(--muted)', fontStyle: 'italic' }}>
          X-Username is a preference, not a password. Pick a name; you can switch any time.
          Letters, digits, underscores. {USERNAME_MIN}–{USERNAME_MAX} characters.
        </p>
      </header>

      {/* Register */}
      <section style={section}>
        <h2 style={sectionH}>Claim a Name</h2>
        <form onSubmit={onCreate}>
          <label htmlFor="signup-name" style={inputLabel}>Username</label>
          <input
            id="signup-name"
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="e.g. kyle_choy"
            autoComplete="off"
            spellCheck={false}
            aria-invalid={showInlineRule}
            aria-describedby="signup-rule"
            style={inputStyle}
          />
          <p
            id="signup-rule"
            style={{
              marginTop: 6,
              fontFamily: 'var(--font-sans)',
              fontSize: 10,
              letterSpacing: '0.16em',
              textTransform: 'uppercase',
              color: showInlineRule ? '#b34a3a' : 'var(--muted)',
            }}
          >
            {showInlineRule
              ? 'Letters, digits, underscores only · 3–20 chars'
              : `${newName.length} / ${USERNAME_MAX}`}
          </p>

          {serverError ? <div style={{ marginTop: 16 }}><ErrorBanner error={serverError} /></div> : null}

          <button
            type="submit"
            disabled={!valid || createMut.isPending}
            style={{
              marginTop: 16,
              background: valid ? 'var(--gold)' : 'var(--hairline)',
              color: 'var(--white)',
              border: 0,
              padding: '8px 22px',
              fontFamily: 'var(--font-sans)',
              fontSize: 11,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              cursor: valid ? 'pointer' : 'not-allowed',
            }}
          >
            {createMut.isPending ? 'Claiming…' : 'Claim Name'}
          </button>
        </form>
      </section>

      {/* Switch */}
      <section style={section}>
        <h2 style={sectionH}>
          Switch Identity {current ? <em style={{ color: 'var(--muted)', fontStyle: 'italic', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--font-serif)' }}>(currently @{current})</em> : null}
        </h2>
        {usersQ.isLoading ? <p style={mutedItalic}>Loading the directory…</p> : null}
        {usersQ.isError ? <ErrorBanner error={usersQ.error} onRetry={() => void usersQ.refetch()} /> : null}
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {usersQ.data?.map((u) => (
            <li
              key={u.username}
              style={{
                padding: '12px 0',
                borderBottom: '1px solid var(--hairline)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: 16,
                  fontWeight: current === u.username ? 500 : 400,
                  color: 'var(--black)',
                }}
              >
                @{u.username}
              </span>
              {current === u.username ? (
                <span style={chip}>active</span>
              ) : (
                <button
                  type="button"
                  onClick={() => onSwitch(u.username)}
                  style={switchBtn}
                >
                  Switch
                </button>
              )}
            </li>
          ))}
        </ul>
        <p style={{ marginTop: 24 }}>
          <Link to="/" style={{ color: 'var(--gold)' }}>Skip — read the Wall →</Link>
        </p>
      </section>
    </div>
  )
}

const section: React.CSSProperties = {
  marginBottom: 40,
  paddingBottom: 32,
  borderBottom: '1px solid var(--gold)',
}

const sectionH: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--black)',
  marginBottom: 16,
  fontWeight: 500,
}

const eyebrow: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 12,
}

const inputLabel: React.CSSProperties = {
  display: 'block',
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.2em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 6,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  fontFamily: 'var(--font-serif)',
  fontSize: 18,
  color: 'var(--black)',
  background: 'transparent',
  border: 'none',
  borderBottom: '1px solid var(--gold)',
  padding: '6px 0',
  outline: 'none',
}

const switchBtn: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  background: 'transparent',
  border: '1px solid var(--gold)',
  padding: '5px 12px',
  cursor: 'pointer',
}

const chip: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--white)',
  background: 'var(--gold)',
  padding: '3px 10px',
}

const mutedItalic: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 14,
  color: 'var(--muted)',
}
