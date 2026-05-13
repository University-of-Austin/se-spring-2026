import { Link } from "react-router-dom";
import type { Post } from "../api/types";

export interface PostRowProps {
  post: Post;
  pending?: boolean;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = Date.now();
  const diffSec = Math.round((now - d.getTime()) / 1000);
  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return d.toLocaleDateString();
}

export function PostRow({ post, pending = false }: PostRowProps) {
  return (
    <article className={`post${pending ? " pending" : ""}`} aria-busy={pending}>
      <div className="post-meta">
        <Link to={`/users/${encodeURIComponent(post.username)}`} className="author">
          {post.username}
        </Link>
        <span>·</span>
        <time
          dateTime={post.created_at}
          title={new Date(post.created_at).toLocaleString()}
        >
          {formatTime(post.created_at)}
        </time>
        {post.updated_at && <span className="edited">(edited)</span>}
        {pending && <span className="pending-tag">posting…</span>}
      </div>
      <div className="post-message">{post.message}</div>
      {!pending && (
        <Link to={`/posts/${post.id}`} className="post-row-link">
          view #{post.id} →
        </Link>
      )}
    </article>
  );
}
