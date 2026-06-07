import { Link } from 'react-router-dom';
import type { Post } from '../api/types';
import { UserChip } from './UserChip';

interface Props {
  post: Post;
  onDelete?: (post: Post) => void;
  deleting?: boolean;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function PostCard({ post, onDelete, deleting }: Props) {
  const pending = post.id < 0;
  return (
    <article className={`post${pending ? ' post--pending' : ''}`} aria-busy={pending || undefined}>
      <header className="post__meta">
        <UserChip username={post.username} />
        <Link to={`/posts/${post.id}`} className="post__time">
          <time dateTime={post.created_at}>{formatTime(post.created_at)}</time>
        </Link>
      </header>
      <p className="post__message">{post.message}</p>
      {onDelete && !pending && (
        <footer className="post__actions">
          <button
            type="button"
            className="btn btn--ghost btn--danger"
            onClick={() => onDelete(post)}
            disabled={deleting}
            aria-label={`Delete post ${post.id}`}
          >
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        </footer>
      )}
    </article>
  );
}
