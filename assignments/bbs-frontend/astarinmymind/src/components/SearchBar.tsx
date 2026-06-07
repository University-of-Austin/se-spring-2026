// Plain controlled search input. The parent owns debouncing — this component
// just renders + reports keystrokes upward. Accepts an optional ref so the
// `/` keyboard shortcut can focus the input programmatically.

import type { ChangeEvent, Ref } from 'react'

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search posts…',
  ref,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  ref?: Ref<HTMLInputElement>
}) {
  return (
    <input
      ref={ref}
      type="search"
      value={value}
      onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label="Search posts"
      className="w-full rounded border border-border bg-bg px-3 py-2 text-text focus:border-accent focus:outline-none"
    />
  )
}
