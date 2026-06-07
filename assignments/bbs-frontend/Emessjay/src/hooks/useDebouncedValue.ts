// Tiny helper: returns the input value with a delay, so that rapid
// changes (typing in a search box) settle to a single value before
// downstream effects fire.  Used by FeedView to avoid hitting the
// backend on every keystroke.

import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);

  return debounced;
}
