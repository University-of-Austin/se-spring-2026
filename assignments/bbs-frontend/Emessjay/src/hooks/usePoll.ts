// Calls `refetch` on a setInterval cadence so a view's data stays
// fresh without the user reloading.  Pauses while the tab is hidden
// (visibilitychange) so a backgrounded tab isn't hammering the API
// for nothing, and fires one immediate refetch when the tab comes
// back so the user sees fresh data on the same beat they re-focus.
//
// useApi keeps existing data on screen during a refetch (state.data
// is preserved, only state.loading flips), so the spinner does not
// flash on the polling interval — the row list just updates in place
// when a new post arrives.

import { useEffect } from "react";

export function usePoll(refetch: () => void, intervalMs: number, enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    let id: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (id !== null) return;
      id = setInterval(refetch, intervalMs);
    };
    const stop = () => {
      if (id === null) return;
      clearInterval(id);
      id = null;
    };

    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        // Immediate catch-up refetch on return-to-tab so the user
        // doesn't have to wait up to intervalMs for the next tick.
        refetch();
        start();
      }
    };

    if (!document.hidden) start();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refetch, intervalMs, enabled]);
}
