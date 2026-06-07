// Shared error state. Every fetch site surfaces failures here -- we never
// swallow errors silently (lecture 5.2 "three failures" guidance).

import styles from "./ErrorMessage.module.css";

interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: Props) {
  return (
    <div className={styles.error} role="alert">
      <p className={styles.text}>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={styles.retry}>
          Try again
        </button>
      )}
    </div>
  );
}
