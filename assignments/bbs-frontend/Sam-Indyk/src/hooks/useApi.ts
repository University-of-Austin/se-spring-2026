import { useEffect, useState, useCallback } from "react";
import { ApiError } from "../api/client";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
}

/**
 * Generic data-loading hook with built-in loading/error states and
 * cancellation on unmount or when the key changes.
 *
 * `fetcher` is given an AbortSignal so it can wire it through to fetch().
 * `deps` controls when the fetch re-fires (treated like useEffect deps).
 *
 * The returned `refetch` re-runs the fetcher without touching `deps`.
 * The returned `setData` lets callers do optimistic updates (e.g. inserting
 * a pending post into the feed list before the server responds).
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>
): ApiState<T> & {
  refetch: () => void;
  setData: (updater: (prev: T | null) => T | null) => void;
} {
  const [data, setDataState] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

  const setData = useCallback(
    (updater: (prev: T | null) => T | null) => {
      setDataState((prev) => updater(prev));
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher(controller.signal)
      .then((result) => {
        if (!cancelled) {
          setDataState(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError) {
          setError(err);
        } else {
          setError(new ApiError(0, String(err), err));
        }
        setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { data, loading, error, refetch, setData };
}
