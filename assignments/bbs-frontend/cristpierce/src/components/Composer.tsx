import { useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { LIMITS } from '../lib/types'
import { toApiError } from '../hooks/useResource'
import { useIdentity } from '../context/IdentityContext'
import { Button } from './ui/Button'
import { CharCounter } from './CharCounter'
import { SendIcon } from './ui/icons'
import styles from './Composer.module.css'

interface ComposerProps {
  /** Performs the post. Should reject with an ApiError so 422s surface inline. */
  onPost: (message: string) => Promise<void>
  autoFocus?: boolean
  placeholder?: string
}

/*
 * Compose form. Client-side validation mirrors the server's rules (1–500 chars)
 * so the Post button disables before the user can hit a 422, the counter turns
 * red past the limit, and Cmd/Ctrl+Enter posts. If the server still returns a
 * 422 (stricter rule, or a bypassed disabled state), its message is shown
 * inline — never swallowed.
 */
export function Composer({ onPost, autoFocus = false, placeholder }: ComposerProps) {
  const { username, isLoggedIn } = useIdentity()
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const helpId = useId()
  const errorId = useId()

  const length = message.length
  const trimmed = message.trim()
  const tooLong = length > LIMITS.messageMax
  const canPost = isLoggedIn && trimmed.length >= LIMITS.messageMin && !tooLong && !pending

  function autoGrow() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 320)}px`
  }

  async function submit() {
    if (!canPost) return
    setPending(true)
    setServerError(null)
    try {
      await onPost(trimmed)
      setMessage('')
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto'
          textareaRef.current.focus()
        }
      })
    } catch (err) {
      const apiErr = toApiError(err)
      setServerError(apiErr.fieldErrors?.message ?? apiErr.message)
    } finally {
      setPending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      submit()
    }
  }

  if (!isLoggedIn) {
    return (
      <div className={styles.signedOut}>
        <p>
          You’re browsing as a guest. <Link to="/login">Choose a username</Link> to post,
          edit, and react.
        </p>
      </div>
    )
  }

  return (
    <form
      className={styles.composer}
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
      aria-label="Compose a new post"
    >
      <label htmlFor="composer-input" className="visually-hidden">
        Write a post as {username}
      </label>
      <textarea
        id="composer-input"
        ref={textareaRef}
        className={styles.textarea}
        value={message}
        placeholder={placeholder ?? 'Share something with the board…'}
        rows={3}
        autoFocus={autoFocus}
        aria-invalid={tooLong || serverError !== null}
        aria-describedby={`${helpId} ${serverError ? errorId : ''}`.trim()}
        onChange={(e) => {
          setMessage(e.target.value)
          setServerError(null)
          autoGrow()
        }}
        onKeyDown={handleKeyDown}
      />

      {serverError && (
        <p id={errorId} className={styles.error} role="alert">
          {serverError}
        </p>
      )}

      <div className={styles.footer}>
        <span id={helpId} className={styles.hint}>
          Posting as <strong>@{username}</strong>
          <span className={styles.kbd}> · ⌘/Ctrl + Enter</span>
        </span>
        <div className={styles.actions}>
          <CharCounter value={length} max={LIMITS.messageMax} />
          <Button type="submit" variant="primary" size="sm" loading={pending} disabled={!canPost}>
            <SendIcon size={15} />
            Post
          </Button>
        </div>
      </div>
    </form>
  )
}
