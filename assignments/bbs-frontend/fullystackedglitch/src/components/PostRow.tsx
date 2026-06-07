import { Link } from "react-router-dom";
import type { Post } from "../lib/types";
import styles from "./PostRow.module.css";

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function PostRow({
  post,
  onDelete,
  deleting,
  showAuthor = true,
}: {
  post: Post;
  onDelete?: (post: Post) => void;
  deleting?: boolean;
  showAuthor?: boolean;
}) {
  return (
    <article
      className={`${styles.row} ${deleting ? styles.rowDeleting : ""}`}
      aria-label={`Post by ${post.username}`}
    >
      <p className={styles.message}>{post.message}</p>
      <div className={styles.meta}>
        <span>
          {showAuthor && (
            <Link to={`/users/${post.username}`} className={styles.author}>
              @{post.username}
            </Link>
          )}
          {showAuthor && " · "}
          <Link to={`/posts/${post.id}`} className={styles.permalink}>
            {formatTimestamp(post.created_at)}
          </Link>
        </span>
        {onDelete && (
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.deleteBtn}
              onClick={() => onDelete(post)}
              disabled={deleting}
              aria-label={`Delete post ${post.id}`}
            >
              {deleting ? "deleting…" : "delete"}
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
