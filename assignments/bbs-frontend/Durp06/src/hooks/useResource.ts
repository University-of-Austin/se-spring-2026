import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/bbs';

export interface ResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

// Shared boilerplate for "fetch on mount, expose data/loading/error, allow
// refetch, cancel inflight on unmount". Every read-side hook (useFeed, useUser,
// etc.) is a thin wrapper around this so loading/error semantics are consistent.
export function useResource<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const ctrl = new AbortController();
    let cancelled = false;
    setLoading(true);
    setError(null);
    fnRef.current(ctrl.signal)
      .then((result) => {
        if (cancelled) return;
        setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if ((err as Error)?.name === 'AbortError') return;
        const msg = err instanceof ApiError ? err.message : (err as Error)?.message ?? 'Unknown error';
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, refetch };
}
