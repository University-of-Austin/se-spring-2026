import { useCallback, useEffect, useRef, useState } from "react";

export type ApiState<T> = {
  data: T | undefined;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

// Generic async-fetch hook. Three states, abort-on-unmount, manual refetch.
// Re-runs when `key` changes (use a stringifiable summary of the inputs).
export function useApi<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  key: string,
): ApiState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [tick, setTick] = useState(0);
  // Keep fn fresh without making it a dep (avoids effect storms when callers
  // pass an inline closure).
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fnRef.current(controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) {
          setData(d);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setLoading(false);
      });
    return () => controller.abort();
  }, [key, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, refetch };
}
