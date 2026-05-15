// One post in a list.
//
// Accessibility: the row itself is *not* a button.  Doing so makes
// nested-interactive HTML (a username <Link> inside a row <button>)
// which screen readers handle poorly and HTML technically forbids.
// Instead, the message is a real <Link> to the post detail; the
// username is a separate <Link> in the footer.  We use :has() in CSS
// to give the whole row a hover background when the user is over the
// message link.

import { Link } from "react-router-dom";
import type { PostOut } from "../api/types";
import { paths } from "../router/paths";
import { UserLink } from "./UserLink";
import { Timestamp } from "./Timestamp";
import styles from "./PostRow.module.css";

export function PostRow({ post }: { post: PostOut }) {
  return (
    <article className={styles.row}>
      <Link to={paths.post(post.id)} className={styles.messageLink}>
        <p className={styles.message}>{post.message}</p>
      </Link>
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
