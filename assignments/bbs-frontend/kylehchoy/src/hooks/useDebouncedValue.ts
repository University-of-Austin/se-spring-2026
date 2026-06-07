import { useEffect, useState } from 'react'

/**
 * Returns the input value after it has been stable for `ms` milliseconds.
 * Used for search-as-you-type so we don't hammer GET /posts?q= on each keystroke.
 */
export function useDebouncedValue<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return debounced
}
