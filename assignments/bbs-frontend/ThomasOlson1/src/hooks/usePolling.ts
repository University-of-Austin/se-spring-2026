import { useEffect, useRef } from "react";

export function usePolling(callback: () => void, intervalMs: number, enabled: boolean = true) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!enabled) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        cbRef.current();
      }
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs, enabled]);
}
