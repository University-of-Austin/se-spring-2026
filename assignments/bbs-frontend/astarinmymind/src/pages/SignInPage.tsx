// Two forms: "switch to existing user" (verifies user exists via GET /users/{name}
// before claiming the identity) and "create new user" (POST /users, then sets).
// X-Username isn't real auth, but checking that the user exists at sign-in time
// gives a much clearer error than discovering it later during a post.

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCurrentUser } from '../context/UserContext'
import { createUser } from '../api/posts'
import { api, ApiError } from '../api/client'

const USERNAME_RE = /^[a-zA-Z0-9_]+$/

function isValidUsername(name: string): boolean {
  return USERNAME_RE.test(name) && name.length >= 3 && name.length <= 20
}

export default function SignInPage() {
  const { setUsername } = useCurrentUser()
  const navigate = useNavigate()

  // Sign-in (existing user) form state
  const [signInName, setSignInName] = useState('')
  const [signInSubmitting, setSignInSubmitting] = useState(false)
  const [signInError, setSignInError] = useState<string | null>(null)

  // Create-user form state
  const [createName, setCreateName] = useState('')
  const [createSubmitting, setCreateSubmitting] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault()
    if (!isValidUsername(signInName)) return
    setSignInSubmitting(true)
    setSignInError(null)
    try {
      // Verify the user exists. ApiError(404) if not.
      await api(`/users/${signInName}`)
      setUsername(signInName)
      navigate('/')
    } catch (err) {
      setSignInError(
        err instanceof ApiError && err.status === 404
          ? `No user "${signInName}" exists yet. Create one below?`
          : err instanceof ApiError
            ? err.detail
            : 'Sign in failed'
      )
      setSignInSubmitting(false)
    }
  }

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!isValidUsername(createName)) return
    setCreateSubmitting(true)
    setCreateError(null)
    try {
      await createUser(createName)
      setUsername(createName)
      navigate('/')
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.detail : 'Failed to create user')
      setCreateSubmitting(false)
    }
  }

  return (
    <div className="space-y-12">
      <h1 className="font-serif text-3xl">Sign in</h1>

      {/* Switch to existing user */}
      <form onSubmit={handleSignIn} className="space-y-3">
        <h2 className="font-serif text-xl">Sign in as existing user</h2>
        <p className="text-sm text-muted">
          X-Username isn't real auth — but I check that the username exists so you
          don't discover the typo on your first post.
        </p>
        <label htmlFor="signin-username" className="block">
          <span className="text-sm">Username</span>
          <input
            id="signin-username"
            type="text"
            value={signInName}
            onChange={(e) => setSignInName(e.target.value)}
            placeholder="3-20 chars, letters/numbers/underscores"
            autoComplete="off"
            disabled={signInSubmitting}
            className="mt-1 block w-full rounded border border-border bg-bg px-3 py-2 text-text focus:border-accent focus:outline-none"
          />
        </label>
        {signInError && <p className="text-sm text-error">{signInError}</p>}
        <button
          type="submit"
          disabled={!isValidUsername(signInName) || signInSubmitting}
          className="rounded bg-accent text-bg px-4 py-2 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {signInSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      {/* Create new user */}
      <form onSubmit={handleCreate} className="space-y-3">
        <h2 className="font-serif text-xl">Create new user</h2>
        <label htmlFor="create-username" className="block">
          <span className="text-sm">New username</span>
          <input
            id="create-username"
            type="text"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder="3-20 chars, letters/numbers/underscores"
            autoComplete="off"
            disabled={createSubmitting}
            className="mt-1 block w-full rounded border border-border bg-bg px-3 py-2 text-text focus:border-accent focus:outline-none"
          />
        </label>
        {createError && <p className="text-sm text-error">{createError}</p>}
        <button
          type="submit"
          disabled={!isValidUsername(createName) || createSubmitting}
          className="rounded bg-accent text-bg px-4 py-2 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {createSubmitting ? 'Creating…' : 'Create user'}
        </button>
      </form>
    </div>
  )
}
