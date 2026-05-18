import type { ReactNode } from "react";
import styles from "./StatusBlock.module.css";

export function LoadingBlock({ label = "Loading…" }: { label?: string }) {
  return (
    <div className={styles.skeleton} aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className={styles.skeletonRow} />
      <div className={styles.skeletonRow} />
      <div className={styles.skeletonRow} />
    </div>
  );
}

export function ErrorBlock({
  error,
  onRetry,
}: {
  error: Error;
  onRetry?: () => void;
}) {
  return (
    <div className={styles.error} role="alert">
      <span>{error.message}</span>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          retry
        </button>
      )}
    </div>
  );
}

export function EmptyBlock({ children }: { children: ReactNode }) {
  return <div className={styles.empty}>{children}</div>;
}
