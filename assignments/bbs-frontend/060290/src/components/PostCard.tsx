import { Link } from 'react-router-dom'
import type { Post } from '../types/bbs'

type PostCardProps = {
  post: Post
}

export function PostCard({ post }: PostCardProps) {
  return (
    <li>
      <article className="post-card">
        <div className="post-card__meta">
          <Link to={`/posts/${post.id}`}>Post #{post.id}</Link>
          {' · '}
          <Link to={`/users/${encodeURIComponent(post.username)}`}>{post.username}</Link>
          {' · '}
          <time dateTime={post.created_at}>{post.created_at}</time>
        </div>
        <p className="post-card__message">{post.message}</p>
      </article>
    </li>
  )
}
