import { Link } from "react-router-dom";
import type { Post } from "../api/types";
import { Timestamp } from "./Timestamp";
import { UserBadge } from "./UserBadge";
import { ReactionBar } from "./ReactionBar";
import styles from "./PostCard.module.css";

export function PostCard({
  post,
  currentUser,
  onDelete,
  showReactions = true,
  optimistic = false,
}: {
  post: Post;
  currentUser: string | null;
  onDelete?: (post: Post) => void;
  showReactions?: boolean;
  /** marks an unsaved (still-flying) post for visual feedback */
  optimistic?: boolean;
}) {
  const isOwn = currentUser && currentUser === post.username;

  return (
    <article
      className={`${styles.card} ${optimistic ? styles.optimistic : ""}`}
      aria-busy={optimistic || undefined}
    >
      <header className={styles.meta}>
        <UserBadge username={post.username} />
        <span className={styles.dot} aria-hidden="true">
          ·
        </span>
        <Link to={`/posts/${post.id}`} className={styles.timeLink}>
          <Timestamp value={post.created_at} />
        </Link>
        {post.updated_at && (
          <span className={styles.edited} title={`edited ${post.updated_at}`}>
            (edited)
          </span>
        )}
        {post.board && post.board !== "general" && (
          <span className={styles.board}>#{post.board}</span>
        )}
      </header>

      <p className={styles.message}>{post.message}</p>

      {showReactions && !optimistic && (
        <ReactionBar postId={post.id} currentUser={currentUser} />
      )}

      {onDelete && !optimistic && (
        <div className={styles.foot}>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => onDelete(post)}
            aria-label={`Delete post ${post.id}`}
          >
            Delete
          </button>
          {!isOwn && (
            <span className="subtle" title="X-Username is not real auth — anyone can delete">
              ⚠ not your post
            </span>
          )}
        </div>
      )}
    </article>
  );
}
