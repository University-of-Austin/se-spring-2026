import type { ApiError } from "../api/client";

export function ErrorBanner({
  error,
  onRetry,
}: {
  error: ApiError | string;
  onRetry?: () => void;
}) {
  const message = typeof error === "string" ? error : error.message;
  const status = typeof error === "string" ? null : error.status;
  return (
    <div className="error-banner" role="alert">
      <strong>{status && status > 0 ? `${status}` : "Error"}</strong>
      <span>{message}</span>
      {onRetry && (
        <button
          type="button"
          className="btn btn-ghost"
          onClick={onRetry}
          style={{ marginLeft: "auto" }}
        >
          Retry
        </button>
      )}
    </div>
  );
}
