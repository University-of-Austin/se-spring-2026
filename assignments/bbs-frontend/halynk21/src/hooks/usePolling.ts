import { useEffect, useRef } from 'react';
// (useEffect is also used to refresh refetchRef per render — see below.)

// Polling lifecycle wrapper. Pass a refetch callback (typically from
// useQuery), an interval, and an enabled flag. We:
//   - skip ticks when document.hidden
//   - skip ticks while the previous one is still in-flight (useRef guard,
//     since refetch returns a Promise we can await)
//   - immediately refetch on visibilitychange→visible and on online
//   - never abort an in-flight request on tab-hide; only future ticks pause
//   - never start the interval while disabled (caller controls when initial
//     load is complete and polling can begin)
export function usePolling(
  refetch: () => Promise<void>,
  { ms, enabled = true }: { ms: number; enabled?: boolean },
): void {
  const refetchRef = useRef(refetch);
  useEffect(() => {
    refetchRef.current = refetch;
  });

  const inFlightRef = useRef<boolean>(false);

  useEffect(() => {
    if (!enabled) return;

    const tick = async (): Promise<void> => {
      if (inFlightRef.current || document.hidden) return;
      inFlightRef.current = true;
      try {
        await refetchRef.current();
      } finally {
        inFlightRef.current = false;
      }
    };

    const interval = window.setInterval(() => {
      void tick();
    }, ms);

    const onVisible = (): void => {
      if (!document.hidden) void tick();
    };
    const onOnline = (): void => {
      void tick();
    };

    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onOnline);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onOnline);
    };
  }, [ms, enabled]);
}
