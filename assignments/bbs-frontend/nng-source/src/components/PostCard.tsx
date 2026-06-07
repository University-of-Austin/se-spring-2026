import { Link } from "react-router-dom";
import { resolveBackendUrl } from "../api";
import type { Post } from "../types";
import { Avatar } from "./Avatar";

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  // YYYY-MM-DD HH:MM (24h, local)
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function PostCard({
  post,
  optimistic = false,
  showDelete = false,
  onDelete,
}: {
  post: Post;
  optimistic?: boolean;
  showDelete?: boolean;
  onDelete?: (id: number) => void;
}) {
  return (
    <article className={`post-card ${optimistic ? "post-card-optimistic" : ""}`} aria-busy={optimistic}>
      <header className="post-card-header">
        <Link to={`/users/${encodeURIComponent(post.username)}`} className="post-username">
          <Avatar username={post.username} src={post.avatar_url} size="sm" />
          <span>{post.username}</span>
        </Link>
        <span className="post-meta">
          <Link to={`/posts/${post.id}`} className="post-id-link">#{post.id}</Link>
          {" · "}
          <time dateTime={post.created_at}>{formatTimestamp(post.created_at)}</time>
          {post.updated_at && <span className="post-edited"> · edited</span>}
          {post.board && (
            <>
              {" · "}
              <Link to={`/?board=${encodeURIComponent(post.board)}`} className="post-board">
                #{post.board}
              </Link>
            </>
          )}
        </span>
      </header>
      <p className="post-message">{post.message}</p>
      {post.image_url && (
        <a
          href={resolveBackendUrl(post.image_url) ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="post-image-link"
          aria-label="Open attached image in a new tab"
        >
          <img
            src={resolveBackendUrl(post.image_url) ?? post.image_url}
            alt=""
            className="post-image"
            loading="lazy"
          />
        </a>
      )}
      {showDelete && !optimistic && onDelete && (
        <div className="post-actions">
          <button
            type="button"
            className="btn btn-link btn-danger"
            onClick={() => onDelete(post.id)}
            aria-label={`Delete post ${post.id}`}
          >
            Delete
          </button>
        </div>
      )}
    </article>
  );
}
