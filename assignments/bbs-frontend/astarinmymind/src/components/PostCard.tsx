// One post in the feed. The whole card is a click target for the post detail
// page (stretched-link pattern): an invisible <Link> covers the article,
// while the UserLink sits above it (z-10) so its own click goes to the profile.

import { Link } from 'react-router-dom'
import type { Post } from '../types'
import { UserLink } from './UserLink'
import { formatTimestamp } from '../lib/format'

export function PostCard({ post }: { post: Post }) {
  return (
    <article className="animate-post-in relative rounded border border-border p-4 space-y-2 hover:bg-highlight hover:border-accent transition-colors">
      {/* Stretched link: invisible, covers the whole card → /posts/:id.
          Anything that should NOT navigate to the post (i.e. UserLink) gets
          `relative z-10` so it sits above this and captures clicks first. */}
      <Link
        to={`/posts/${post.id}`}
        aria-label={`Open post #${post.id}`}
        data-no-active-bg
        className="absolute inset-0"
      />

      {/* whitespace-pre-wrap preserves newlines the user typed. */}
      <p className="whitespace-pre-wrap text-text">{post.message}</p>

      <div className="flex items-center justify-between text-sm text-muted">
        <UserLink username={post.username} className="relative z-10" />
        <span>
          {formatTimestamp(post.created_at)}
          {post.updated_at && <span className="ml-1">(edited)</span>}
        </span>
      </div>
    </article>
  )
}
