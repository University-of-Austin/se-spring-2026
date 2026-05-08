// One post in the feed. Pure presentation — takes a Post prop, renders it.
// No state, no fetches, just JSX. Reused in FeedPage and UserProfilePage.

import { Link } from 'react-router-dom'
import type { Post } from '../types'
import { UserLink } from './UserLink'

export function PostCard({ post }: { post: Post }) {
  return (
    <article className="rounded border border-border p-4 space-y-2 hover:border-text/30 transition-colors">
      {/* whitespace-pre-wrap preserves newlines the user typed. */}
      <p className="whitespace-pre-wrap text-text">{post.message}</p>

      <div className="flex items-center justify-between text-sm text-muted">
        <UserLink username={post.username} />
        <Link
          to={`/posts/${post.id}`}
          className="font-mono hover:text-text"
        >
          {new Date(post.created_at).toLocaleString()}
          {post.updated_at && <span className="ml-1">(edited)</span>}
        </Link>
      </div>
    </article>
  )
}
