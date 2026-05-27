import { ApiError } from "../api/types";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="status" role="status" aria-live="polite">
      {label}
    </div>
  );
}

export function ErrorBlock({
  error,
  onRetry,
}: {
  error: ApiError;
  onRetry?: () => void;
}) {
  const heading =
    error.status === 0
      ? "Can't reach the server"
      : `Request failed (HTTP ${error.status})`;
  return (
    <div className="status error" role="alert">
      <div className="error-heading">{heading}</div>
      <div className="error-detail">{error.detail}</div>
      {onRetry && (
        <button type="button" className="link-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
