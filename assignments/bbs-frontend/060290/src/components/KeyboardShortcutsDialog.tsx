import { useEffect, useId, useRef } from 'react'
import './KeyboardShortcutsDialog.css'

type KeyboardShortcutsDialogProps = {
  open: boolean
  onClose: () => void
}

export function KeyboardShortcutsDialog({ open, onClose }: KeyboardShortcutsDialogProps) {
  const titleId = useId()
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    closeRef.current?.focus()
  }, [open])

  if (!open) {
    return null
  }

  return (
    <div
      className="kbd-overlay"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div
        className="kbd-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="kbd-dialog__header">
          <h2 id={titleId} className="kbd-dialog__title">
            Keyboard shortcuts
          </h2>
          <button
            ref={closeRef}
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <ul className="kbd-list">
          <li>
            <kbd className="kbd-key">⌘</kbd> + <kbd className="kbd-key">Enter</kbd> or{' '}
            <kbd className="kbd-key">Ctrl</kbd> + <kbd className="kbd-key">Enter</kbd> — Submit
            message on Compose
          </li>
          <li>
            <kbd className="kbd-key">Shift</kbd> + <kbd className="kbd-key">?</kbd> — Open this
            panel (when focus is not in a text field)
          </li>
          <li>
            <kbd className="kbd-key">/</kbd> — Go to Feed and focus search (when focus is not in a
            text field)
          </li>
          <li>
            <kbd className="kbd-key">Escape</kbd> — Close this panel
          </li>
        </ul>
      </div>
    </div>
  )
}
