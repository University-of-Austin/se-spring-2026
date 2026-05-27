import { Link } from "react-router-dom";
import type { Post } from "../api/types";

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function PostRow({
  post,
  showAuthor = true,
  canDelete = false,
  pending = false,
  deleting = false,
  errorMessage = null,
  onDelete,
}: {
  post: Post;
  showAuthor?: boolean;
  canDelete?: boolean;
  pending?: boolean;
  deleting?: boolean;
  errorMessage?: string | null;
  onDelete?: (post: Post) => void;
}) {
  return (
    <article
      className={
        "post-row" +
        (pending ? " pending" : "") +
        (deleting ? " deleting" : "")
      }
      aria-busy={pending || deleting}
    >
      <div className="post-message">{post.message}</div>
      <div className="post-meta">
        {showAuthor && (
          <Link
            to={`/users/${encodeURIComponent(post.username)}`}
            className="link-btn"
          >
            @{post.username}
          </Link>
        )}
        <Link
          to={`/posts/${post.id}`}
          className="link-btn muted"
          aria-label={`Open post ${post.id}`}
        >
          {formatTime(post.created_at)}
          {post.updated_at ? " · edited" : ""}
          {pending ? " · sending…" : ""}
        </Link>
        {canDelete && onDelete && !pending && (
          <button
            type="button"
            className="link-btn muted post-delete"
            onClick={() => onDelete(post)}
            disabled={deleting}
            aria-label={`Delete post ${post.id}`}
          >
            {deleting ? "deleting…" : "delete"}
          </button>
        )}
      </div>
      {errorMessage && (
        <div className="status error inline" role="alert">
          <div className="error-detail">{errorMessage}</div>
        </div>
      )}
    </article>
  );
}
