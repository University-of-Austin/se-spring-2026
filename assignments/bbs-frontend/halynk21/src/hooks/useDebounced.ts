import { useEffect, useState } from 'react';

// Returns `value` debounced by `ms`. Used for the search input — every
// keystroke updates immediate state but only the debounced value is the
// queryKey for useFeed's useQuery, so we don't refetch on every character.
export function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);

  return debounced;
}
