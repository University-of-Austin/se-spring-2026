import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApiError, deletePost } from '../api/bbs';
import { usePost } from '../hooks/usePost';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { UserChip } from '../components/UserChip';
import { useToast } from '../hooks/useToast';

export default function PostDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const numericId = Number(id);
  const post = usePost(numericId);
  const navigate = useNavigate();
  const { push } = useToast();
  const [deleting, setDeleting] = useState(false);

  const onDelete = useCallback(async () => {
    if (!post.data) return;
    setDeleting(true);
    try {
      await deletePost(post.data.id);
      push('Post deleted.', 'info');
      navigate('/');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : (err as Error).message;
      push(`Couldn't delete post: ${msg}`, 'error');
      setDeleting(false);
    }
  }, [post.data, navigate, push]);

  if (Number.isNaN(numericId)) {
    return <p className="empty">Invalid post id.</p>;
  }
  if (post.loading) return <Loading label="Loading post" />;
  if (post.error) {
    if (/not found/i.test(post.error)) {
      return (
        <section className="page page--post">
          <h1>Post #{id}</h1>
          <p className="empty">No such post.</p>
          <Link to="/" className="btn btn--ghost">
            ← Back to feed
          </Link>
        </section>
      );
    }
    return <ErrorMessage message={post.error} onRetry={post.refetch} />;
  }
  if (!post.data) return null;

  return (
    <section className="page page--post">
      <header className="page__head">
        <Link to="/" className="btn btn--ghost btn--sm">
          ← Back to feed
        </Link>
      </header>
      <article className="post post--detail">
        <header className="post__meta">
          <UserChip username={post.data.username} />
          <time dateTime={post.data.created_at}>
            {new Date(post.data.created_at).toLocaleString()}
          </time>
        </header>
        <p className="post__message post__message--lg">{post.data.message}</p>
        <footer className="post__actions">
          <button
            type="button"
            className="btn btn--danger"
            onClick={onDelete}
            disabled={deleting}
            aria-label={`Delete post ${post.data.id}`}
          >
            {deleting ? 'Deleting…' : 'Delete post'}
          </button>
        </footer>
      </article>
    </section>
  );
}
