import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deletePost, getPost } from "../api/posts";
import { ApiError } from "../api/types";
import { useFetch } from "../hooks/useFetch";
import { Loading, ErrorBlock } from "../components/StatusBlock";

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function PostDetailView({ id }: { id: number }) {
  const navigate = useNavigate();
  const fetcher = useCallback(() => getPost(id), [id]);
  const { data, error, loading, reload } = useFetch(fetcher, [id]);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    if (!data) return;
    if (!window.confirm(`Delete post #${data.id}? This can't be undone.`)) {
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePost(data.id);
      navigate("/");
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : String(err));
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <section className="view post-view">
        <Loading label={`Loading post ${id}…`} />
      </section>
    );
  }

  if (error) {
    if (error.status === 404) {
      return (
        <section className="view post-view">
          <h1>Post not found</h1>
          <p className="muted">
            Post #{id} doesn't exist (or was deleted).
          </p>
          <Link to="/" className="secondary">
            ← Back to feed
          </Link>
        </section>
      );
    }
    return (
      <section className="view post-view">
        <ErrorBlock error={error} onRetry={reload} />
      </section>
    );
  }

  if (!data) return null;

  return (
    <section className="view post-view">
      <h1>Post #{data.id}</h1>
      <article className="post-detail">
        <div className="post-message big">{data.message}</div>
        <div className="post-meta">
          <Link
            to={`/users/${encodeURIComponent(data.username)}`}
            className="link-btn"
          >
            @{data.username}
          </Link>
          <span className="muted">{formatTime(data.created_at)}</span>
          {data.updated_at && (
            <span className="muted small">
              edited {formatTime(data.updated_at)}
            </span>
          )}
        </div>
      </article>

      <div className="actions">
        <Link to="/" className="secondary">
          ← Back
        </Link>
        <button
          type="button"
          className="danger"
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? "Deleting…" : "Delete post"}
        </button>
      </div>

      {deleteError && (
        <div className="status error" role="alert">
          <div className="error-detail">{deleteError}</div>
        </div>
      )}
    </section>
  );
}
