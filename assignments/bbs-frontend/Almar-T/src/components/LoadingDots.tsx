import styles from "./LoadingDots.module.css";

export function LoadingDots({ label = "Loading" }: { label?: string }) {
  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className="sr-only">{label}</span>
    </div>
  );
}
