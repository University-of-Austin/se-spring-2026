// Renders an optimistic post entry — one of three visual states:
//   pending   muted, with "sending…"
//   confirmed normal styling, brief crossover before being removed
//   failed    red border, error detail, Retry / Dismiss buttons

import type { PendingPost } from "../hooks/useOptimisticPosts";
import { Timestamp } from "./Timestamp";
import styles from "./PendingPostRow.module.css";

type Props = {
  post: PendingPost;
  onRetry: () => void;
  onDismiss: () => void;
};

export function PendingPostRow({ post, onRetry, onDismiss }: Props) {
  const variantClass =
    post.status === "failed" ? styles.failed :
    post.status === "confirmed" ? styles.confirmed :
    styles.pending;

  return (
    <article className={`${styles.row} ${variantClass}`} aria-live="polite">
      <p className={styles.message}>{post.message}</p>
      <footer className={styles.meta}>
        <span className={styles.user}>@{post.username}</span>
        <span className={styles.dot} aria-hidden>·</span>
        <Timestamp iso={post.createdAt} />
        <span className={styles.dot} aria-hidden>·</span>
        {post.status === "pending" && <span className={styles.statusText}>sending…</span>}
        {post.status === "confirmed" && <span className={styles.statusText}>posted ✓</span>}
        {post.status === "failed" && <span className={styles.statusError}>failed to send</span>}
      </footer>
      {post.status === "failed" && (
        <div className={styles.failedDetails}>
          <p className={styles.errorDetail}>{post.errorDetail}</p>
          <div className={styles.actions}>
            <button type="button" className={styles.retry} onClick={onRetry}>Retry</button>
            <button type="button" className={styles.dismiss} onClick={onDismiss}>Dismiss</button>
          </div>
        </div>
      )}
    </article>
  );
}
