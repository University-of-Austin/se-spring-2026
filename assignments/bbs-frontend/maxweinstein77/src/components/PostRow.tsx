// One row in the feed. Avatar + author (clickable -> profile), timestamp
// (clickable -> post detail), message body with @mentions, and an
// optional delete button.

import { Link } from "react-router-dom";
import type { Post } from "../types";
import { avatarColor, avatarInitial } from "../lib/avatar";
import { formatRelativeTime } from "../lib/formatTime";
import { Mentions } from "./Mentions";
import { ReactionButton } from "./ReactionButton";
import styles from "./PostRow.module.css";

interface Props {
  post: Post;
  onDelete?: (postId: number) => void;
  deleting?: boolean;
}

export function PostRow({ post, onDelete, deleting }: Props) {
  return (
    <article className={styles.row}>
      <Link to={`/users/${post.username}`} className={styles.avatarLink} aria-hidden="true" tabIndex={-1}>
        <span
          className={styles.avatar}
          style={{ background: avatarColor(post.username) }}
        >
          {avatarInitial(post.username)}
        </span>
      </Link>
      <div className={styles.body}>
        <header className={styles.meta}>
          <Link to={`/users/${post.username}`} className={styles.author}>
            {post.username}
          </Link>
          <Link to={`/posts/${post.id}`} className={styles.time}>
            {formatRelativeTime(post.created_at)}
          </Link>
        </header>
        <p className={styles.message}><Mentions text={post.message} /></p>
        <div className={styles.actions}>
          {post.id > 0 && <ReactionButton postId={post.id} />}
          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(post.id)}
              disabled={deleting}
              className={styles.deleteBtn}
              aria-label={`Delete post by ${post.username}`}
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
