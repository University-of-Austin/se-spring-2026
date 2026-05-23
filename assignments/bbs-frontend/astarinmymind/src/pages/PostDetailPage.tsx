// One post on its own page, with a delete button when signed in.
// Bronze allows anyone to delete (X-Username isn't real auth — see A2 README).

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { usePost } from '../hooks/usePost'
import { useCurrentUser } from '../context/useCurrentUser'
import { deletePost } from '../api/posts'
import { ApiError } from '../api/client'
import { UserLink } from '../components/UserLink'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { formatTimestamp } from '../lib/format'

export default function PostDetailPage() {
  const { id: idParam = '' } = useParams()
  const id = Number(idParam)
  const { post, loading, error } = usePost(id)
  const { username } = useCurrentUser()
  const navigate = useNavigate()

  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!username) return
    if (!window.confirm('Delete this post? This cannot be undone.')) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await deletePost(id, username)
      navigate('/')
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : 'Delete failed')
      setDeleting(false)
    }
  }

  // Garbage id (e.g. /posts/foo) — Number(...) returned NaN
  if (Number.isNaN(id)) {
    return (
      <div className="text-center py-12 space-y-3">
        <h1 className="font-serif text-4xl font-bold">Invalid post id</h1>
        <Link to="/" className="underline underline-offset-2 decoration-muted/60 hover:text-accent hover:decoration-accent transition-colors">← Back to feed</Link>
      </div>
    )
  }

  if (loading) return <Spinner />

  // 404 → dedicated "not found" view (per spec)
  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="text-center py-12 space-y-3">
        <h1 className="font-serif text-4xl font-bold">Post not found</h1>
        <p className="text-muted">No post with id #{id} exists.</p>
        <Link to="/" className="underline underline-offset-2 decoration-muted/60 hover:text-accent hover:decoration-accent transition-colors">← Back to feed</Link>
      </div>
    )
  }

  if (error) return <ErrorMessage error={error} />
  if (!post) return null

  return (
    <article className="space-y-4">
      <p className="whitespace-pre-wrap text-text text-lg">{post.message}</p>

      <div className="flex items-center justify-between text-sm text-muted">
        <UserLink username={post.username} />
        <span>
          {formatTimestamp(post.created_at)}
          {post.updated_at && <span className="ml-1">(edited)</span>}
        </span>
      </div>

      {username && (
        <div className="space-y-2">
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="rounded border border-error text-error px-4 py-2 hover:bg-error/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
          {deleteError && <p className="text-sm text-error">{deleteError}</p>}
        </div>
      )}
    </article>
  )
}
