import type { ApiError } from "../api/types";
import styles from "./ErrorBanner.module.css";

export function ErrorBanner({
  error,
  onRetry,
}: {
  error: ApiError | string;
  onRetry?: () => void;
}) {
  const detail = typeof error === "string" ? error : error.detail;
  const status = typeof error === "string" ? null : error.status;
  return (
    <div className={styles.banner} role="alert">
      <div className={styles.body}>
        <strong className={styles.title}>
          {status ? `Error ${status}` : "Something went wrong"}
        </strong>
        <p className={styles.detail}>{detail}</p>
      </div>
      {onRetry && (
        <button className="btn" onClick={onRetry} type="button">
          Try again
        </button>
      )}
    </div>
  );
}
