import { Link } from 'react-router-dom';
import type { PostOut } from '../api/types';
import { relative } from '../lib/time';

type Props = {
  post: PostOut;
  onDelete?: (id: number) => void;
  deleteDisabled?: boolean;
  showDetailLink?: boolean;
};

export function PostCard({ post, onDelete, deleteDisabled, showDetailLink = true }: Props) {
  return (
    <article className="card">
      <div className="card__header">
        <div>
          <Link to={`/users/${encodeURIComponent(post.username)}`} className="card__author">
            @{post.username}
          </Link>
          {post.updated_at && (
            <span className="card__meta" style={{ marginLeft: 'var(--space-2)' }}>
              (edited)
            </span>
          )}
        </div>
        <div className="card__meta">
          {showDetailLink ? (
            <Link to={`/posts/${post.id}`} className="card__meta">
              {relative(post.created_at)}
            </Link>
          ) : (
            <span>{relative(post.created_at)}</span>
          )}
        </div>
      </div>
      <div className="card__body">{post.message}</div>
      {onDelete && (
        <div className="card__actions">
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => onDelete(post.id)}
            disabled={deleteDisabled}
            aria-label={`Delete post ${post.id}`}
          >
            Delete
          </button>
        </div>
      )}
    </article>
  );
}
