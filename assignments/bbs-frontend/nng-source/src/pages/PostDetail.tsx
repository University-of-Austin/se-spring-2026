import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ApiError, type Post } from "../types";
import { useAuth } from "../auth";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";

export function PostDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { username, token } = useAuth();

  const numericId = Number(id);
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isFinite(numericId)) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const p = await api.getPost(numericId);
      setPost(p);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else setError(err instanceof Error ? err.message : "Could not load post.");
    } finally {
      setLoading(false);
    }
  }, [numericId]);

  useEffect(() => { void load(); }, [load]);

  async function onDelete() {
    if (!token || !post) return;
    if (!confirm(`Delete post #${post.id}?`)) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deletePost(post.id, token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete post.");
      setDeleting(false);
    }
  }

  if (loading) return <div className="page"><Spinner /></div>;
  if (notFound) {
    return (
      <div className="page page-notfound">
        <h1>Post not found</h1>
        <p>No post exists with id <code>{id}</code>.</p>
        <Link to="/" className="btn btn-secondary">Back to feed</Link>
      </div>
    );
  }
  if (error && !post) return <div className="page"><ErrorBox message={error} onRetry={load} /></div>;
  if (!post) return null;

  const isAuthor = !!username && username === post.username;
  const ts = new Date(post.created_at).toLocaleString();

  return (
    <div className="page page-post-detail">
      <Link to="/" className="btn btn-link back-link">&larr; Back to feed</Link>
      <article className="post-detail">
        <header>
          <Link to={`/users/${encodeURIComponent(post.username)}`} className="post-username">
            {post.username}
          </Link>
          <span className="post-meta"> · #{post.id} · {ts}</span>
          {post.updated_at && <span className="post-edited"> · edited</span>}
        </header>
        <p className="post-message post-message-detail">{post.message}</p>
        {token && (
          <div className="post-actions">
            <button
              type="button"
              className="btn btn-danger"
              disabled={deleting || !isAuthor}
              onClick={onDelete}
              aria-label={`Delete post ${post.id}`}
              title={isAuthor ? "Delete this post" : "Only the author can delete"}
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        )}
        {error && <div role="alert" className="inline-error">{error}</div>}
      </article>
    </div>
  );
}
