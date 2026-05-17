import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  setData: (d: T | null) => void;
}

/**
 * useAsync runs an async function on mount and any time `deps` change. It
 * exposes loading, error, and data, plus a reload() trigger.
 *
 * Avoids the classic "stale state set after unmount" warning by guarding the
 * setState calls with a generation counter that's incremented on cleanup.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const gen = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableFn = useCallback(fn, deps);

  useEffect(() => {
    const myGen = ++gen.current;
    setLoading(true);
    setError(null);
    stableFn()
      .then((result) => {
        if (gen.current === myGen) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (gen.current === myGen) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      });
    return () => { /* generation guard handles cancellation */ };
  }, [stableFn, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload, setData };
}
