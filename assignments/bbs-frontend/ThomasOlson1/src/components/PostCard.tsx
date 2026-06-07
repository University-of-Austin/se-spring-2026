import { Link } from "react-router-dom";
import type { Post } from "../api/client";

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

type Props = {
  post: Post;
  showDelete?: boolean;
  onDelete?: (id: number) => void;
  pending?: boolean;
};

export function PostCard({ post, showDelete = false, onDelete, pending = false }: Props) {
  return (
    <article className={`post-card ${pending ? "post-card-pending" : ""}`}>
      <header className="post-card-head">
        <Link to={`/users/${encodeURIComponent(post.username)}`} className="post-card-author">
          @{post.username}
        </Link>
        <span className="post-card-board" aria-label="board">
          {post.board}
        </span>
        <Link to={`/posts/${post.id}`} className="post-card-time">
          {formatTimestamp(post.created_at)}
        </Link>
      </header>
      <p className="post-card-msg">{post.message}</p>
      <footer className="post-card-foot">
        {post.updated_at && (
          <span className="post-card-edited" title={`Edited ${formatTimestamp(post.updated_at)}`}>
            edited
          </span>
        )}
        {showDelete && onDelete && (
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={() => onDelete(post.id)}
            disabled={pending}
          >
            Delete
          </button>
        )}
      </footer>
    </article>
  );
}
