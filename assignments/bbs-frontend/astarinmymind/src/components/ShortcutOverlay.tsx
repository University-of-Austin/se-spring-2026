// Modal listing keyboard shortcuts. Opened by pressing `?`, dismissed by
// Escape or clicking the backdrop. Layout owns its open/close state so the
// `?` shortcut works from any page.

type Props = {
  open: boolean
  onClose: () => void
}

const SHORTCUTS = [
  { keys: '⌘ Enter', description: 'Post message' },
  { keys: '/', description: 'Focus search' },
  { keys: '?', description: 'Toggle this overlay' },
  { keys: 'Esc', description: 'Close overlay' },
]

export function ShortcutOverlay({ open, onClose }: Props) {
  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-heading"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Dim backdrop — clicking it closes */}
      <div className="absolute inset-0 bg-text/30" aria-hidden="true" />

      {/* Panel — clicks inside don't bubble to the backdrop */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative bg-bg border border-border rounded-lg p-6 max-w-sm w-full space-y-4"
      >
        <h2 id="shortcuts-heading" className="font-serif text-xl">
          Keyboard shortcuts
        </h2>
        <dl className="space-y-2 text-sm">
          {SHORTCUTS.map(({ keys, description }) => (
            <div key={keys} className="flex items-center justify-between">
              <dt className="text-text">{description}</dt>
              <dd>
                <kbd className="font-mono text-muted">{keys}</kbd>
              </dd>
            </div>
          ))}
        </dl>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-muted hover:text-text"
        >
          Close
        </button>
      </div>
    </div>
  )
}
