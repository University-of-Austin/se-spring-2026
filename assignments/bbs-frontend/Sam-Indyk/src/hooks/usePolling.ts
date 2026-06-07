import { useEffect, useRef } from "react";

/**
 * Calls `tick` every `intervalMs` while `enabled` is true. Pauses while the
 * tab is hidden (avoids burning requests when the user isn't looking) and
 * pauses across the network-offline event.
 */
export function usePolling(
  tick: () => void,
  intervalMs: number,
  enabled = true
): void {
  // Keep tick in a ref so we don't reset the interval on every render.
  const tickRef = useRef(tick);
  useEffect(() => {
    tickRef.current = tick;
  }, [tick]);

  useEffect(() => {
    if (!enabled) return;

    let timer: number | null = null;

    const start = () => {
      if (timer !== null) return;
      timer = window.setInterval(() => {
        if (document.visibilityState === "visible" && navigator.onLine) {
          tickRef.current();
        }
      }, intervalMs);
    };
    const stop = () => {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") start();
      else stop();
    };

    start();
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("online", start);
    window.addEventListener("offline", stop);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("online", start);
      window.removeEventListener("offline", stop);
    };
  }, [intervalMs, enabled]);
}
