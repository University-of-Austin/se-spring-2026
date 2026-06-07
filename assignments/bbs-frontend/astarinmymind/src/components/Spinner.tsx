// Loading indicator. role/aria-live make it announceable to screen readers.

export function Spinner() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 text-muted text-sm py-4"
    >
      <span className="inline-block h-2 w-2 rounded-full bg-muted animate-pulse" />
      Loading…
    </div>
  )
}
