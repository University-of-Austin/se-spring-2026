import type { ApiError } from '../api/client';

export function ErrorBox({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <div>{error.message}</div>
      {onRetry && (
        <button type="button" className="btn btn--sm btn--ghost" onClick={onRetry} style={{ marginTop: 'var(--space-2)' }}>
          Try again
        </button>
      )}
    </div>
  );
}
