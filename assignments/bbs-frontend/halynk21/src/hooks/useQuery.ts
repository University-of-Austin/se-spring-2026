import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

export type QueryResult<T> = {
  data: T | undefined;
  loading: boolean;        // true only when there's no data yet
  revalidating: boolean;   // true when refetching with stale data on screen
  error: ApiError | null;
  refetch: () => Promise<void>;
};

// Generic data hook. Accepts a fetcher that takes an AbortSignal and a deps
// array (the "query key" — when it changes, the in-flight request aborts and
// a new one starts). refetch returns a Promise so usePolling can await it.
export function useQuery<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
): QueryResult<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(true);
  const [revalidating, setRevalidating] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Latest fetcher in a ref so refetch (called by usePolling, manual buttons,
  // etc.) always closes over the newest version without being a useCallback dep.
  // The effect (no deps) runs after every render, before any event handler or
  // poll tick gets to read the ref, so the "latest" guarantee holds.
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const abortRef = useRef<AbortController | null>(null);
  const hasDataRef = useRef<boolean>(false);

  const doFetch = useCallback(async (): Promise<void> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (hasDataRef.current) setRevalidating(true);
    else setLoading(true);

    try {
      const result = await fetcherRef.current(controller.signal);
      if (controller.signal.aborted) return;
      setData(result);
      setError(null);
      hasDataRef.current = true;
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      if (controller.signal.aborted) return;
      if (err instanceof ApiError) setError(err);
      else setError(new ApiError(0, err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
        setRevalidating(false);
      }
    }
  }, []);

  // Refetch on mount and on every deps change. Cleanup aborts in-flight
  // requests on unmount and on the next deps change (covering the
  // query-key-change case the v3 plan flagged).
  useEffect(() => {
    void doFetch();
    return () => {
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, revalidating, error, refetch: doFetch };
}
