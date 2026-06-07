import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { bbsApi } from '../api/bbs'
import { useFeedOptimistic } from '../context/FeedOptimisticContext'
import { useMutation } from '../hooks/useMutation'
import { useUsername } from '../hooks/useUsername'
import { ServerValidationErrors } from '../components/ServerValidationErrors'
import './pages.css'

const MIN = 1
const MAX = 500

export function ComposePage() {
  const { username } = useUsername()
  const { setOptimisticPost, refetchFeed } = useFeedOptimistic()
  const [message, setMessage] = useState('')
  const [clientError, setClientError] = useState<string | null>(null)

  const postFn = useCallback(
    (body: string) => {
      if (!username) {
        return Promise.reject(
          new Error('Select a username on Sign up / user before posting.'),
        )
      }
      return bbsApi.createPost(username, body)
    },
    [username],
  )

  const { state, mutate, reset } = useMutation(postFn)

  function validate(text: string): string | null {
    const len = text.length
    if (len < MIN || len > MAX) {
      return `Message must be between ${MIN} and ${MAX} characters (currently ${len}).`
    }
    return null
  }

  const submitIfValid = useCallback(async () => {
    setClientError(null)
    const err = validate(message)
    if (err) {
      setClientError(err)
      return
    }
    if (!username) {
      return
    }
    const optimistic = {
      id: -Date.now(),
      username,
      message,
      created_at: new Date().toISOString(),
    }
    setOptimisticPost(optimistic)
    const result = await mutate(message)
    setOptimisticPost(null)
    if (result) {
      await refetchFeed()
    }
  }, [message, mutate, refetchFeed, setOptimisticPost, username])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await submitIfValid()
  }

  function handleMessageKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== 'Enter' || !(e.metaKey || e.ctrlKey)) {
      return
    }
    e.preventDefault()
    void submitIfValid()
  }

  const busy = state.phase === 'loading'
  const showForm = state.phase === 'idle' || state.phase === 'error' || busy
  const len = message.length
  const overMax = len > MAX
  const empty = len === 0
  const submitDisabled = busy || !username || empty || overMax

  return (
    <div className="page">
      <h1>Compose</h1>
      {!username ? (
        <p className="empty-hint">
          Choose a username on <Link to="/account">Sign up / user</Link> before composing.
        </p>
      ) : null}

      {busy ? (
        <div className="inline-status inline-status--loading" role="status">
          <p>Posting your message…</p>
        </div>
      ) : null}

      {state.phase === 'success' ? (
        <div className="inline-status inline-status--success" role="status">
          <p>
            Message posted.{' '}
            <Link to={`/posts/${state.data.id}`}>View post #{state.data.id}</Link>
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              reset()
              setMessage('')
            }}
          >
            Write another
          </button>
        </div>
      ) : null}

      {showForm ? (
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="compose-message">Message ({MIN}–{MAX} characters)</label>
            <textarea
              id="compose-message"
              name="message"
              value={message}
              onChange={(ev) => {
                setMessage(ev.target.value)
                setClientError(null)
              }}
              onKeyDown={handleMessageKeyDown}
              aria-invalid={!!clientError || overMax}
              aria-describedby="compose-hint compose-err compose-server-err"
              disabled={busy || !username}
            />
            {state.phase === 'error' ? (
              <div
                id="compose-server-err"
                className="compose-field-error"
                role="alert"
              >
                {state.httpStatus === 422 ? (
                  <>
                    <p className="compose-field-error__title">The server could not validate this.</p>
                    <ServerValidationErrors body={state.body} />
                  </>
                ) : (
                  <p>{state.message}</p>
                )}
              </div>
            ) : (
              <span id="compose-server-err" className="visually-hidden" />
            )}
            <p
              id="compose-hint"
              className={`field-hint${overMax ? ' field-hint--over' : ''}`}
            >
              {len} / {MAX} characters
            </p>
            {clientError ? (
              <p id="compose-err" className="field-error">
                {clientError}
              </p>
            ) : null}
          </div>
          <button type="submit" className="btn" disabled={submitDisabled}>
            Post
          </button>
        </form>
      ) : null}
    </div>
  )
}
