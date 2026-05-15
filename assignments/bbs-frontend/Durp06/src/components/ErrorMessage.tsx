interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: Props) {
  return (
    <div className="error" role="alert">
      <div className="error__title">Something went wrong</div>
      <div className="error__body">{message}</div>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
