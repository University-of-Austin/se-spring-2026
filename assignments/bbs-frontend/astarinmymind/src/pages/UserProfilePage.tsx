// Profile for one user: their info + their posts.
// Spec calls out a 404 view if the user doesn't exist — we distinguish that
// from generic fetch failures via `error instanceof ApiError && status === 404`.

import { useParams, Link } from 'react-router-dom'
import { useUser } from '../hooks/useUser'
import { PostCard } from '../components/PostCard'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { ApiError } from '../api/client'
import { formatDate } from '../lib/format'

export default function UserProfilePage() {
  const { username = '' } = useParams()
  const { user, posts, loading, error } = useUser(username)

  if (loading) return <Spinner />

  // 404 → dedicated "not found" view (per spec)
  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="text-center py-12 space-y-3">
        <h1 className="font-serif text-4xl font-bold">User not found</h1>
        <p className="text-muted">No user "@{username}" exists.</p>
        <Link to="/users" className="underline underline-offset-2 decoration-muted/60 hover:text-accent hover:decoration-accent transition-colors">
          ← Back to all users
        </Link>
      </div>
    )
  }

  // Other errors → generic error message
  if (error) return <ErrorMessage error={error} />

  // Defensive: should never happen — if loading=false and error=null, user is set.
  if (!user) return null

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-serif text-4xl font-bold">@{user.username}</h1>
        {user.bio && <p className="text-text">{user.bio}</p>}
        <p className="text-sm text-muted">
          Joined {formatDate(user.created_at)}
          {' · '}
          {user.post_count} {user.post_count === 1 ? 'post' : 'posts'}
        </p>
      </header>

      {posts.length === 0
        ? <p className="text-muted">No posts yet.</p>
        : <div
            // calc(100vh - 240px) makes the box fill what remains below the
            // header so it ends at roughly the same distance from the page
            // bottom as the feed's scroll window.
            style={{ maxHeight: 'calc(100vh - 240px)' }}
            className="space-y-3 overflow-y-auto scrollbar-hide"
            aria-live="polite"
          >
            {posts.map(post => <PostCard key={post.id} post={post} />)}
          </div>
      }
    </div>
  )
}
