export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="error-box">
      <strong>Something went wrong.</strong>
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn btn-secondary">
          Try again
        </button>
      )}
    </div>
  );
}
