import { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { deletePost, getPost, patchPost } from "../api/posts";
import { useFetch } from "../hooks/useFetch";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

export function PostDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const postId = Number(id);
  const navigate = useNavigate();
  const { username: me } = useAuth();
  const { push } = useToast();

  const fetcher = useCallback((signal: AbortSignal) => getPost(postId, signal), [postId]);
  const { data, loading, error, status, refetch, setData } = useFetch(fetcher, [postId]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  if (Number.isNaN(postId))
    return (
      <div className="page">
        <h1>Invalid post id</h1>
      </div>
    );
  if (loading) return <Spinner label="Loading post…" />;
  if (status === 404)
    return (
      <div className="page">
        <h1>Post not found</h1>
        <p>
          <Link to="/">← Back to feed</Link>
        </p>
      </div>
    );
  if (error || !data) return <ErrorBanner message={error ?? "Failed to load post"} onRetry={refetch} />;

  const isAuthor = me === data.username;

  async function doDelete() {
    if (!me) {
      push("Sign in to delete", "error");
      return;
    }
    setBusy(true);
    try {
      await deletePost(postId, me);
      push("Post deleted", "info");
      navigate("/");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Failed to delete", "error");
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!me) return;
    setBusy(true);
    try {
      const updated = await patchPost(postId, draft, me);
      setData(updated);
      setEditing(false);
      push("Post updated", "info");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Failed to update post", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page post-detail">
      <p className="breadcrumb">
        <Link to="/">← Feed</Link>
      </p>
      <article className="post-card post-card-detail">
        <header className="post-card-head">
          <Link to={`/users/${encodeURIComponent(data.username)}`} className="post-card-author">
            @{data.username}
          </Link>
          <span className="post-card-board">{data.board}</span>
          <time>{new Date(data.created_at + "Z").toLocaleString()}</time>
        </header>
        {!editing && <p className="post-card-msg">{data.message}</p>}
        {editing && (
          <div className="compose">
            <label htmlFor="edit-msg" className="visually-hidden">Edit message</label>
            <textarea
              id="edit-msg"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={4}
              maxLength={500}
            />
            <div className="row">
              <span className="compose-count">{draft.length}/500</span>
              <button type="button" className="btn btn-primary" onClick={saveEdit} disabled={busy || draft.trim().length === 0}>
                {busy ? "Saving…" : "Save"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}
        {data.updated_at && !editing && (
          <p className="post-card-edited-note">
            Edited {new Date(data.updated_at + "Z").toLocaleString()}
          </p>
        )}
        {!editing && (
          <div className="row">
            {isAuthor && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setDraft(data.message);
                  setEditing(true);
                }}
              >
                Edit
              </button>
            )}
            <button type="button" className="btn btn-danger" onClick={doDelete} disabled={busy}>
              Delete
            </button>
            {!isAuthor && me && (
              <span className="hint">
                You're signed in as @{me}. Backend will reject delete/edit for non-authors with 403.
              </span>
            )}
          </div>
        )}
      </article>
    </div>
  );
}
