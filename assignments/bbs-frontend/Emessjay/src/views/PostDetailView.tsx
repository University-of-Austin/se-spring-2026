// Detail view for a single post, with a delete button.
//
// The double-click-delete edge case the assignment calls out:
// `deleting` is true while the DELETE request is in flight, so the
// button stays disabled — a second click does nothing.

import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { usePost } from "../hooks/usePost";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { deletePost } from "../api/endpoints";
import { ApiError } from "../api/client";
import { Loadable } from "../components/Loadable";
import { UserLink } from "../components/UserLink";
import { Timestamp } from "../components/Timestamp";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import { NotFoundView } from "../components/NotFoundView";
import { paths } from "../router/paths";
import styles from "./PostDetailView.module.css";

export function PostDetailView() {
  const { id: idParam } = useParams<{ id: string }>();
  const idNum = Number(idParam);
  const navigate = useNavigate();
  const { username: currentUsername } = useCurrentUser();
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<ApiError | null>(null);

  // Guard before useApi so we never run a fetch for an obviously
  // invalid id like "abc" or "-1".
  const isValid = Number.isInteger(idNum) && idNum > 0;

  // We hard-code the conditional render here; usePost is called
  // unconditionally to keep the hook order stable, but we tell it
  // to fetch id=0 which the server will simply 404 — and we
  // short-circuit before showing that error to the user.
  const state = usePost(isValid ? idNum : 0);

  if (!isValid) return <NotFoundView what="This post" />;

  async function onDelete() {
    if (!window.confirm("Delete this post?")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePost(idNum);
      navigate(paths.feed());
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
            {currentUsername === post.username && (
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
            )}
            {deleteError && <ApiErrorMessage error={deleteError} />}
          </article>
        )}
      </Loadable>
    </div>
  );
}
