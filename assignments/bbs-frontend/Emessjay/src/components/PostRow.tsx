// One post in a list.  Whole row is clickable (navigates to detail);
// the username inside is a separate clickable region (navigates to
// profile, stops propagation in UserLink).

import { useRouter } from "../router/useRouter";
import type { PostOut } from "../api/types";
import { UserLink } from "./UserLink";
import { Timestamp } from "./Timestamp";
import styles from "./PostRow.module.css";

export function PostRow({ post }: { post: PostOut }) {
  const { navigate } = useRouter();

  return (
    <article
      className={styles.row}
      onClick={() => navigate({ view: "post", id: post.id })}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          navigate({ view: "post", id: post.id });
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Post by ${post.username}: ${post.message}`}
    >
      <p className={styles.message}>{post.message}</p>
      <footer className={styles.meta}>
        <UserLink username={post.username} />
        <span className={styles.dot} aria-hidden>·</span>
        <Timestamp iso={post.created_at} />
        {post.updated_at && (
          <>
            <span className={styles.dot} aria-hidden>·</span>
            <span className={styles.edited}>edited</span>
          </>
        )}
      </footer>
    </article>
  );
}
