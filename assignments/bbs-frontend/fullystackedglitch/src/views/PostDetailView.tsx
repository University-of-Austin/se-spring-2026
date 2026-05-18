import { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ErrorBlock, LoadingBlock } from "../components/StatusBlock";
import { useApi } from "../hooks/useApi";
import { ApiError, api } from "../lib/api";
import styles from "./PostDetailView.module.css";

export function PostDetailView() {
  const { id = "" } = useParams<{ id: string }>();
  const postId = Number(id);
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetcher = useCallback(
    (signal: AbortSignal) => api.getPost(postId, signal),
    [postId],
  );
  const { data, loading, error, refetch } = useApi(fetcher, `post:${postId}`);

  if (!Number.isFinite(postId) || postId <= 0) {
    return (
      <div className={styles.notFound}>
        <h1>invalid post id</h1>
        <Link to="/">back to feed</Link>
      </div>
    );
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className={styles.notFound}>
        <h1>post not found</h1>
        <p>this post doesn't exist (or was deleted).</p>
        <Link to="/">back to feed</Link>
      </div>
    );
  }

  const onDelete = async () => {
    if (!data) return;
    if (!confirm("delete this post?")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deletePost(data.id);
      navigate("/");
    } catch (e) {
      setDeleteError(
        e instanceof ApiError ? e.message : (e as Error).message ?? "delete failed",
      );
      setDeleting(false);
    }
  };

  return (
    <section className={styles.wrap}>
      {loading && <LoadingBlock label="Loading post" />}
      {error && !(error instanceof ApiError && error.status === 404) && (
        <ErrorBlock error={error} onRetry={refetch} />
      )}
      {data && (
        <article className={styles.card}>
          <div className={styles.meta}>
            <Link to={`/users/${data.username}`} className={styles.author}>
              @{data.username}
            </Link>{" "}
            · {new Date(data.created_at).toLocaleString()}
            {data.updated_at && " · edited"}
          </div>
          <p className={styles.message}>{data.message}</p>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnDanger}
              onClick={onDelete}
              disabled={deleting}
            >
              {deleting ? "deleting…" : "delete"}
            </button>
            <Link to="/" className={styles.btnGhost}>
              back
            </Link>
          </div>
          {deleteError && (
            <span role="alert" style={{ color: "var(--danger)", fontSize: 13 }}>
              {deleteError}
            </span>
          )}
        </article>
      )}
    </section>
  );
}
