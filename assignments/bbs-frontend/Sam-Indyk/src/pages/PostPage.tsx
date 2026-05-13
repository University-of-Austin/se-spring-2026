import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { PostRow } from "../components/PostRow";
import { Spinner } from "../components/Spinner";
import { useApi } from "../hooks/useApi";

export function PostPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [deleteError, setDeleteError] = useState<ApiError | null>(null);

  const numericId = Number(id);
  const isValidId = !Number.isNaN(numericId) && numericId > 0;

  const { data, loading, error, refetch } = useApi(
    (signal) =>
      isValidId
        ? api.getPost(numericId, signal)
        : Promise.reject(new ApiError(400, "Invalid post id", null)),
    [numericId, isValidId]
  );

  async function handleDelete() {
    if (!data) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deletePost(data.id);
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteError(
        err instanceof ApiError ? err : new ApiError(0, String(err), err)
      );
      setDeleting(false);
    }
  }

  if (!isValidId) {
    return (
      <EmptyState
        title="Invalid post id"
        action={<Link to="/" className="btn">Back to feed</Link>}
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading post" />;

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    if (notFound) {
      return (
        <EmptyState
          title={`Post #${id} not found`}
          description="It may have been deleted."
          action={<Link to="/" className="btn">Back to feed</Link>}
        />
      );
    }
    return <ErrorBanner error={error} onRetry={refetch} />;
  }

  if (!data) return null;

  return (
    <>
      <div className="page-header">
        <h1>Post #{data.id}</h1>
        <Link to="/" className="btn btn-ghost">
          ← Back to feed
        </Link>
      </div>

      <PostRow post={data} />

      {deleteError && (
        <div style={{ marginTop: "var(--sp-3)" }}>
          <ErrorBanner error={deleteError} />
        </div>
      )}

      <div className="btn-row" style={{ marginTop: "var(--sp-4)" }}>
        {!confirming && (
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => setConfirming(true)}
          >
            Delete post
          </button>
        )}
        {confirming && (
          <>
            <span className="field-hint">Delete this post? This can't be undone.</span>
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Deleting…
                </>
              ) : (
                "Confirm delete"
              )}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setConfirming(false)}
              disabled={deleting}
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </>
  );
}
