import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/types";

export type FetchState<T> = {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  refetch: () => void;
  setData: (updater: T | ((curr: T | null) => T | null)) => void;
};

/**
 * Generic data fetch with loading/error/data states.
 *
 * `pollMs` enables background polling — only fires when the tab is
 * visible (no point hammering the server while the user is in
 * another tab) and doesn't flash the loading state, so polled
 * refreshes are invisible unless the data actually changes.
 *
 * `setData` exposes the internal cache so callers can apply
 * optimistic updates and reconcile against later refetches.
 */
export function useFetch<T>(
  fn: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
  options: { pollMs?: number } = {},
): FetchState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);

  const fnRef = useRef(fn);
  fnRef.current = fn;

  // Monotonic counter — old in-flight requests are discarded so a
  // stale slow response can't overwrite the result of a newer fast
  // one (the classic "stale render" race).
  const reqIdRef = useRef(0);

  const run = useCallback(async (isPoll: boolean) => {
    const myId = ++reqIdRef.current;
    if (!isPoll) setLoading(true);
    try {
      const next = await fnRef.current();
      if (myId !== reqIdRef.current) return;
      setDataState(next);
      setError(null);
    } catch (e) {
      if (myId !== reqIdRef.current) return;
      setError(e instanceof ApiError ? e : new ApiError(0, String(e)));
    } finally {
      if (myId === reqIdRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!options.pollMs) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void run(true);
    }, options.pollMs);
    return () => window.clearInterval(id);
  }, [options.pollMs, run]);

  const setData = useCallback(
    (updater: T | ((curr: T | null) => T | null)) => {
      if (typeof updater === "function") {
        setDataState((curr) =>
          (updater as (curr: T | null) => T | null)(curr),
        );
      } else {
        setDataState(updater);
      }
    },
    [],
  );

  return { data, error, loading, refetch: () => run(false), setData };
}
