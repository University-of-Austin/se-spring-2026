// Inline error block, used next to form fields when a request fails.
// Distinct from Loadable's error UI (which is for whole-view loads).

import type { ApiError } from "../api/client";
import styles from "./ApiErrorMessage.module.css";

export function ApiErrorMessage({ error }: { error: ApiError }) {
  return (
    <p className={styles.message} role="alert">
      {error.detail}
    </p>
  );
}
