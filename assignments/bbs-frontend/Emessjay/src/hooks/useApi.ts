// Generic { data, loading, error, refetch } hook.
//
// Most resource hooks (usePosts, useUser, …) are one-liners that
// hand a fetcher function to useApi.  The non-obvious parts are:
//
//   1. cleanup() sets an `ignore` flag.  When the effect re-runs
//      because deps changed (e.g. the search query changed), the
//      previous fetch may still be in-flight.  When it eventually
//      resolves, we ignore the result rather than letting a stale
//      response overwrite the newer state.  This is the classic
//      stale-fetch bug that agents skip.
//
//   2. We pass an AbortSignal into the fetcher and abort it on
//      cleanup.  That cancels the network request itself, not just
//      our reaction to it — kinder to the backend and the user's
//      battery.
//
//   3. The initial state is { data: null, loading: true, error: null }
//      so first-paint always shows loading.  Components never need
//      to write "if (!data && !error) return spinner" themselves.

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";

export type ApiState<T> = {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
};

export type Fetcher<T> = (signal: AbortSignal) => Promise<T>;

export type UseApiResult<T> = ApiState<T> & {
  refetch: () => void;
};

export function useApi<T>(
  fetcher: Fetcher<T>,
  deps: ReadonlyArray<unknown>,
): UseApiResult<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  // refetchCounter is a state value we bump from refetch() to force
  // the effect to re-run without changing the caller's deps.  Bumping
  // it triggers the effect, which re-runs the fetcher.
  const [refetchCounter, setRefetchCounter] = useState(0);

  const refetch = useCallback(() => {
    setRefetchCounter((n) => n + 1);
  }, []);

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    setState((s) => ({ data: s.data, loading: true, error: null }));

    fetcher(controller.signal)
      .then((data) => {
        if (ignore) return;
        setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (ignore) return;
        // AbortError happens on cleanup; not a real error to surface.
        if (err instanceof DOMException && err.name === "AbortError") return;
        const apiErr =
          err instanceof ApiError
            ? err
            : new ApiError(0, err instanceof Error ? err.message : String(err));
        setState({ data: null, loading: false, error: apiErr });
      });

    return () => {
      ignore = true;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refetchCounter]);

  return { ...state, refetch };
}
