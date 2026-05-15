// Detail view for a single post, with a delete button.
//
// The double-click-delete edge case the assignment calls out:
// `deleting` is true while the DELETE request is in flight, so the
// button stays disabled — a second click does nothing.  After
// success, we navigate to /feed before any re-render that might
// notice the post is gone (which would render a 404 view through
// usePost re-running for an id that no longer exists).

import { useState } from "react";
import { usePost } from "../hooks/usePost";
import { useRouter } from "../router/useRouter";
import { deletePost } from "../api/endpoints";
import { ApiError } from "../api/client";
import { Loadable } from "../components/Loadable";
import { UserLink } from "../components/UserLink";
import { Timestamp } from "../components/Timestamp";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import { NotFoundView } from "../components/NotFoundView";
import styles from "./PostDetailView.module.css";

export function PostDetailView({ id }: { id: number }) {
  const state = usePost(id);
  const { navigate } = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<ApiError | null>(null);

  async function onDelete() {
    if (!window.confirm("Delete this post?")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePost(id);
      navigate({ view: "feed" });
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err : new ApiError(0, "Delete failed"));
      setDeleting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <Loadable state={state} notFoundView={<NotFoundView what="This post" />}>
        {(post) => (
          <article className={styles.post}>
            <p className={styles.message}>{post.message}</p>
            <footer className={styles.meta}>
              <UserLink username={post.username} />
              <span aria-hidden> · </span>
              <Timestamp iso={post.created_at} />
              {post.updated_at && (
                <>
                  <span aria-hidden> · </span>
                  <em>edited <Timestamp iso={post.updated_at} /></em>
                </>
              )}
            </footer>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.delete}
                onClick={onDelete}
                disabled={deleting}
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
            {deleteError && <ApiErrorMessage error={deleteError} />}
          </article>
        )}
      </Loadable>
    </div>
  );
}
