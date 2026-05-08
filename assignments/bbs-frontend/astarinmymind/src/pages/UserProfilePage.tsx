// Profile for one user: their info + their posts.
// Spec calls out a 404 view if the user doesn't exist — we distinguish that
// from generic fetch failures via `error instanceof ApiError && status === 404`.

import { useParams, Link } from 'react-router-dom'
import { useUser } from '../hooks/useUser'
import { PostCard } from '../components/PostCard'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { ApiError } from '../api/client'

export default function UserProfilePage() {
  const { username = '' } = useParams()
  const { user, posts, loading, error } = useUser(username)

  if (loading) return <Spinner />

  // 404 → dedicated "not found" view (per spec)
  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="text-center py-12 space-y-3">
        <h1 className="font-serif text-3xl">User not found</h1>
        <p className="text-muted">No user "@{username}" exists.</p>
        <Link to="/users" className="text-accent hover:underline">
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
      <header className="space-y-2 border-b border-border pb-4">
        <h1 className="font-serif text-3xl">@{user.username}</h1>
        {user.bio && <p className="text-text">{user.bio}</p>}
        <p className="text-sm text-muted font-mono">
          Joined {new Date(user.created_at).toLocaleDateString()}
          {' · '}
          {user.post_count} {user.post_count === 1 ? 'post' : 'posts'}
        </p>
      </header>

      <div>
        <h2 className="font-serif text-xl mb-3">Posts</h2>
        {posts.length === 0
          ? <p className="text-muted">No posts yet.</p>
          : <div className="space-y-3">
              {posts.map(post => <PostCard key={post.id} post={post} />)}
            </div>
        }
      </div>
    </div>
  )
}
