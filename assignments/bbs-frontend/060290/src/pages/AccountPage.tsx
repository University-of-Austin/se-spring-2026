import { useCallback, useState } from 'react'
import { bbsApi } from '../api/bbs'
import { useMutation } from '../hooks/useMutation'
import { useUsername } from '../hooks/useUsername'
import { ServerValidationErrors } from '../components/ServerValidationErrors'
import './pages.css'

const USERNAME_RE = /^[A-Za-z0-9_]+$/

function signupClientError(u: string): string | null {
  const t = u.trim()
  if (t.length < 3 || t.length > 32) {
    return 'Username must be between 3 and 32 characters.'
  }
  if (!USERNAME_RE.test(t)) {
    return 'Username may only contain letters, digits, or underscores.'
  }
  return null
}

export function AccountPage() {
  const { username, setUsername } = useUsername()
  const [signupName, setSignupName] = useState('')
  const [switchName, setSwitchName] = useState('')
  const [signupClient, setSignupClient] = useState<string | null>(null)

  const signup = useCallback((u: string) => bbsApi.createUser(u.trim()), [])
  const { state: signupState, mutate: runSignup, reset: resetSignup } =
    useMutation(signup)

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    setSignupClient(null)
    const err = signupClientError(signupName)
    if (err) {
      setSignupClient(err)
      return
    }
    const created = await runSignup(signupName.trim())
    if (created) {
      setUsername(created.username)
    }
  }

  function handleSwitch(e: React.FormEvent) {
    e.preventDefault()
    const next = switchName.trim()
    if (!next) {
      return
    }
    setUsername(next)
  }

  return (
    <div className="page">
      <h1>Sign up / switch user</h1>
      <p className="field-hint">
        Signing up calls the server to create an account. Switching only updates this browser
        (use it if you already exist on the server).
      </p>

      <section aria-labelledby="current-label">
        <h2 id="current-label">Current posting user</h2>
        {username ? (
          <p>
            <strong>{username}</strong>
          </p>
        ) : (
          <p className="empty-hint">None selected.</p>
        )}
      </section>

      <section aria-labelledby="signup-label">
        <h2 id="signup-label">Sign up (POST /users)</h2>

        {signupState.phase === 'loading' ? (
          <div className="inline-status inline-status--loading" role="status">
            <p>Creating account…</p>
          </div>
        ) : null}

        {signupState.phase === 'error' ? (
          <div className="inline-status inline-status--error" role="alert">
            {signupState.httpStatus === 422 ? (
              <>
                <p className="fetch-state__title">The server could not validate this username.</p>
                <ServerValidationErrors body={signupState.body} />
              </>
            ) : (
              <p>{signupState.message}</p>
            )}
          </div>
        ) : null}

        {signupState.phase === 'success' ? (
          <div className="inline-status inline-status--success" role="status">
            <p>
              Account <strong>{signupState.data.username}</strong> is ready. You can post as this
              user now.
            </p>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                resetSignup()
                setSignupName('')
              }}
            >
              Register another
            </button>
          </div>
        ) : null}

        {signupState.phase === 'idle' || signupState.phase === 'error' ? (
          <form onSubmit={handleSignup} noValidate>
            <div className="field">
              <label htmlFor="signup-username">New username</label>
              <input
                id="signup-username"
                name="username"
                autoComplete="username"
                value={signupName}
                onChange={(ev) => {
                  setSignupName(ev.target.value)
                  setSignupClient(null)
                }}
                aria-invalid={!!signupClient}
                aria-describedby="signup-hint signup-err"
              />
              <p id="signup-hint" className="field-hint">
                3–32 characters: letters, digits, or underscores.
              </p>
              {signupClient ? (
                <p id="signup-err" className="field-error">
                  {signupClient}
                </p>
              ) : null}
            </div>
            <button type="submit" className="btn">
              Create account
            </button>
          </form>
        ) : null}
      </section>

      <section aria-labelledby="switch-label">
        <h2 id="switch-label">Switch posting user (local only)</h2>
        <form onSubmit={handleSwitch}>
          <div className="field">
            <label htmlFor="switch-username">Username to post as</label>
            <input
              id="switch-username"
              name="switchUsername"
              value={switchName}
              onChange={(ev) => setSwitchName(ev.target.value)}
              autoComplete="username"
            />
            <p className="field-hint">Updates local storage immediately. The server is not checked.</p>
          </div>
          <button type="submit" className="btn btn-secondary">
            Save as current user
          </button>
        </form>
      </section>
    </div>
  )
}
