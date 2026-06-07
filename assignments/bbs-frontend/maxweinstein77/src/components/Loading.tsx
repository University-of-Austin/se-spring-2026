// Shared loading state. Every fetch site uses this so the UX is consistent
// and we never ship a blank screen during a request (lecture 7.1, A4 spec).

import styles from "./Loading.module.css";

interface Props {
  label?: string;
}

export function Loading({ label = "Loading..." }: Props) {
  return (
    <div className={styles.loading} role="status" aria-live="polite">
      {label}
    </div>
  );
}
