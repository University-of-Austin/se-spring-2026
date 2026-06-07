import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export type FetchState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  status: number | null;
  refetch: () => void;
  setData: (updater: T | null | ((prev: T | null) => T | null)) => void;
};

export function useFetch<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>,
): FetchState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcherRef
      .current(controller.signal)
      .then((value) => {
        if (cancelled) return;
        setDataState(value);
        setStatus(200);
      })
      .catch((err: unknown) => {
        if ((err as { name?: string })?.name === "AbortError") return;
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message);
          setStatus(err.status);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
          setStatus(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadKey]);

  const refetch = useCallback(() => setReloadKey((k) => k + 1), []);
  const setData = useCallback(
    (updater: T | null | ((prev: T | null) => T | null)) => {
      setDataState((prev) =>
        typeof updater === "function" ? (updater as (p: T | null) => T | null)(prev) : updater,
      );
    },
    [],
  );

  return { data, loading, error, status, refetch, setData };
}
