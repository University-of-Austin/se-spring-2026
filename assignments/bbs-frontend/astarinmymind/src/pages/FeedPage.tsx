// The feed: ComposeForm at the top (when signed in), then the post list.
// Three explicit branches for loading / error / success — no `posts.map` over
// undefined, no silent failures.

import { Link } from 'react-router-dom'
import { usePosts } from '../hooks/usePosts'
import { useCurrentUser } from '../context/UserContext'
import { PostCard } from '../components/PostCard'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { ComposeForm } from '../components/ComposeForm'

export default function FeedPage() {
  const { posts, loading, error, refetch } = usePosts({ limit: 20 })
  const { username } = useCurrentUser()

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl">Feed</h1>

      {username ? (
        <ComposeForm onPosted={refetch} />
      ) : (
        <p className="text-sm text-muted">
          <Link to="/signin" className="text-accent hover:underline">Sign in</Link> to post.
        </p>
      )}

      {loading && <Spinner />}
      {error && <ErrorMessage error={error} />}
      {!loading && !error && (
        posts.length === 0
          ? <p className="text-muted">No posts yet.</p>
          : <div className="space-y-3">
              {posts.map(post => <PostCard key={post.id} post={post} />)}
            </div>
      )}
    </div>
  )
}
