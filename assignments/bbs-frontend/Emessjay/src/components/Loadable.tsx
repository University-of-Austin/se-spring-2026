// The single place loading / error / empty UI lives.
//
// Components pass a useApi result and a render function for the
// success case.  Loadable picks which branch to show.  This is the
// counter to the named anti-pattern in the assignment ("agents will
// write data.map(...) with no guard for the loading state"): if you
// want to render the data, you have to go through here.
//
// `emptyMessage` is optional; when the data is an empty array we
// show it instead of the success children.  For non-array data
// (single user, single post) this branch never fires.

import type { ReactNode } from "react";
import { Spinner } from "./Spinner";
import styles from "./Loadable.module.css";
import { ApiError } from "../api/client";

type Props<T> = {
  state: {
    data: T | null;
    loading: boolean;
    error: ApiError | null;
    refetch: () => void;
  };
  children: (data: T) => ReactNode;
  emptyMessage?: string;
  notFoundView?: ReactNode;
};

export function Loadable<T>({ state, children, emptyMessage, notFoundView }: Props<T>) {
  if (state.error) {
    if (state.error.status === 404 && notFoundView) return <>{notFoundView}</>;
    return (
      <div className={styles.error} role="alert">
        <p className={styles.errorMessage}>{state.error.detail}</p>
        <button type="button" className={styles.retry} onClick={state.refetch}>
          Try again
        </button>
      </div>
    );
  }

  if (state.data === null) {
    if (state.loading) {
      return (
        <div className={styles.loading} role="status" aria-live="polite">
          <Spinner />
          <span>Loading…</span>
        </div>
      );
    }
    return null;
  }

  if (Array.isArray(state.data) && state.data.length === 0 && emptyMessage) {
    return <p className={styles.empty}>{emptyMessage}</p>;
  }

  return <>{children(state.data)}</>;
}
