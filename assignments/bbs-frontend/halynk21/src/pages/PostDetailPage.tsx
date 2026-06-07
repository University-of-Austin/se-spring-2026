import { useCallback } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '../hooks/useQuery';
import { useMutation } from '../hooks/useMutation';
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';
import { api } from '../api/endpoints';
import { PostCard } from '../components/PostCard';
import { Skeleton } from '../components/Skeleton';
import { ErrorBox } from '../components/ErrorBox';

export function PostDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const postId = Number(id);
  const navigate = useNavigate();
  const { toast } = useToast();
  const confirm = useConfirm();

  const fetcher = useCallback(
    (signal: AbortSignal) => api.getPost(postId, { signal }),
    [postId],
  );
  const { data, loading, error, refetch } = useQuery(fetcher, [postId]);

  // Inline mutation: success/error side effects fire from the callbacks, not
  // from the mutate() return value (void mutations can't distinguish them
  // via return value). 404 = "already gone" → treat as success.
  const del = useMutation<number, void>(
    (pid) => api.deletePost(pid),
    {
      onSuccess: () => {
        toast('success', 'Post deleted.');
        navigate('/');
      },
      onError: (err) => {
        if (err.status === 404) {
          toast('info', 'That post was already gone.');
          navigate('/');
          return;
        }
        toast('error', err.message || "Couldn't delete the post.");
      },
    },
  );

  if (Number.isNaN(postId)) {
    return (
      <>
        <div className="page-header"><h1>Invalid post id</h1></div>
        <div className="empty-state">
          "{id}" is not a number.
          <div style={{ marginTop: 'var(--space-3)' }}>
            <Link to="/" className="btn btn--ghost btn--sm">Back to feed</Link>
          </div>
        </div>
      </>
    );
  }

  if (error?.status === 404) {
    return (
      <>
        <div className="page-header"><h1>Post not found</h1></div>
        <div className="empty-state">
          Post #{postId} no longer exists. Maybe it was deleted.
          <div style={{ marginTop: 'var(--space-3)' }}>
            <Link to="/" className="btn btn--ghost btn--sm">Back to feed</Link>
          </div>
        </div>
      </>
    );
  }

  async function handleDelete(): Promise<void> {
    const ok = await confirm({
      title: 'Delete this post?',
      message: 'This cannot be undone.',
      confirmLabel: 'Delete',
      destructive: true,
    });
    if (!ok) return;
    await del.mutate(postId);
  }

  return (
    <>
      <div className="page-header">
        <h1>Post #{postId}</h1>
        <Link to="/" className="page-header__sub">← Feed</Link>
      </div>

      {loading && <Skeleton count={1} />}
      {error && error.status !== 404 && (
        <ErrorBox error={error} onRetry={() => void refetch()} />
      )}
      {data && (
        <>
          <PostCard post={data} showDetailLink={false} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => void handleDelete()}
              disabled={del.isPending}
            >
              {del.isPending ? 'Deleting...' : 'Delete post'}
            </button>
          </div>
        </>
      )}
    </>
  );
}
