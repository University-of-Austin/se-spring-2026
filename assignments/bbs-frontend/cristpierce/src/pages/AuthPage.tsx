import { useId, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import { LIMITS } from '../lib/types'
import { useUsers } from '../hooks/resources'
import { toApiError } from '../hooks/useResource'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import { Avatar } from '../components/Avatar'
import { PageHeader } from '../components/PageBits'
import { Button } from '../components/ui/Button'
import { ErrorView, LoadingBlock } from '../components/ui/StateView'
import styles from './AuthPage.module.css'

export function AuthPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { username: me, setUsername } = useIdentity()
  const users = useUsers()

  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [existing, setExisting] = useState<string | null>(null)

  const helpId = useId()
  const errorId = useId()

  const trimmed = name.trim()
  const validLength =
    trimmed.length >= LIMITS.usernameMin && trimmed.length <= LIMITS.usernameMax
  const validPattern = trimmed.length === 0 || LIMITS.usernamePattern.test(trimmed)
  // validLength already requires >= 3 chars, so this also excludes the empty case.
  const valid = validLength && validPattern

  function switchTo(username: string) {
    setUsername(username)
    toast.success(`Now posting as @${username}`)
    navigate('/')
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!valid || pending) return
    setPending(true)
    setError(null)
    setExisting(null)
    try {
      await api.createUser(trimmed)
      switchTo(trimmed)
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setExisting(trimmed)
      } else {
        const apiErr = toApiError(err)
        setError(apiErr.fieldErrors?.username ?? apiErr.message)
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <div className={styles.page}>
      <PageHeader
        title="Sign in"
        subtitle="Pick a username to act as. This is an honor-system identity — no password — so it’s really just choosing who you post as."
      />

      {me && (
        <p className={styles.current}>
          Currently posting as <strong>@{me}</strong>. Choose another below to switch.
        </p>
      )}

      <form className={styles.card} onSubmit={handleCreate} aria-label="Create a new user">
        <h2 className={styles.cardTitle}>Create a new user</h2>
        <label htmlFor="new-username" className={styles.label}>
          Username
        </label>
        <input
          id="new-username"
          className={styles.input}
          value={name}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="e.g. ada_lovelace"
          aria-invalid={(!validPattern && trimmed.length > 0) || error !== null}
          aria-describedby={`${helpId} ${error ? errorId : ''}`.trim()}
          onChange={(e) => {
            setName(e.target.value)
            setError(null)
            setExisting(null)
          }}
        />
        <p id={helpId} className={styles.help}>
          {LIMITS.usernameMin}–{LIMITS.usernameMax} characters · letters, digits, and
          underscores only
          {trimmed.length > 0 && !validPattern && (
            <span className={styles.helpBad}> · that contains an invalid character</span>
          )}
        </p>

        {error && (
          <p id={errorId} className={styles.error} role="alert">
            {error}
          </p>
        )}

        {existing && (
          <div className={styles.existing} role="alert">
            <span>
              <strong>@{existing}</strong> already exists.
            </span>
            <Button variant="primary" size="sm" onClick={() => switchTo(existing)}>
              Log in as @{existing}
            </Button>
          </div>
        )}

        <Button type="submit" variant="primary" loading={pending} disabled={!valid}>
          Create &amp; sign in
        </Button>
      </form>

      <section className={styles.card} aria-label="Switch to an existing user">
        <h2 className={styles.cardTitle}>Or switch to an existing user</h2>
        {users.isLoading && users.data === undefined ? (
          <LoadingBlock label="Loading users…" />
        ) : users.isError && users.data === undefined ? (
          <ErrorView error={users.error} onRetry={users.refetch} title="Couldn’t load users" />
        ) : users.data && users.data.length === 0 ? (
          <p className={styles.help}>No users yet — create the first one above.</p>
        ) : (
          <ul className={styles.switchList}>
            {users.data?.map((u) => (
              <li key={u.username}>
                <button
                  type="button"
                  className={`${styles.switchRow} ${u.username === me ? styles.isMe : ''}`}
                  onClick={() => switchTo(u.username)}
                >
                  <Avatar username={u.username} size={32} />
                  <span className={styles.switchName}>{u.username}</span>
                  {u.username === me && <span className={styles.badge}>current</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
