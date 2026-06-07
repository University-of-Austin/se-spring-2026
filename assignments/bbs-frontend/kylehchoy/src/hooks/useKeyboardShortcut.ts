import { useEffect } from 'react'

/**
 * Bind a single-key shortcut.
 * Skips when the user is typing in an input/textarea, when modifier
 * keys are pressed (Cmd/Ctrl/Alt), and when the active target is
 * contentEditable.
 */
export function useKeyboardShortcut(
  key: string,
  handler: () => void,
  enabled: boolean = true,
): void {
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const target = e.target as HTMLElement | null
      if (!target) return
      if (target.isContentEditable) return
      const tag = target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === key) {
        e.preventDefault()
        handler()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [key, handler, enabled])
}
