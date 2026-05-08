// The feed: read-only for now (compose form arrives in Phase 3).
// Three explicit branches for loading / error / success — no `posts.map` over
// undefined, no silent failures.

import { usePosts } from '../hooks/usePosts'
import { PostCard } from '../components/PostCard'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'

export default function FeedPage() {
  const { posts, loading, error } = usePosts({ limit: 20 })

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl">Feed</h1>

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
