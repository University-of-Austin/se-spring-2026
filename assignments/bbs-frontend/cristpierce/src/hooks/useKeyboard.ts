/*
 * Global keyboard handling. Two pieces:
 *   - isTypingTarget(): so single-key shortcuts never fire while the user is
 *     typing into an input/textarea (that would be infuriating).
 *   - useKeydown(): a stable window keydown subscription.
 *   - SHORTCUTS: the single source of truth for the shortcut list, consumed by
 *     both the handler in Layout and the "?" overlay that documents them.
 */

import { useEffect, useRef } from 'react'

export interface Shortcut {
  keys: string
  label: string
}

export const SHORTCUTS: Shortcut[] = [
  { keys: '⌘ / Ctrl + Enter', label: 'Post the message you’re composing' },
  { keys: '/', label: 'Focus the feed search box' },
  { keys: 'c', label: 'Compose a new post' },
  { keys: 'h', label: 'Go to the feed (home)' },
  { keys: 'u', label: 'Go to the user list' },
  { keys: 't', label: 'Toggle light / dark theme' },
  { keys: '?', label: 'Show this shortcuts help' },
  { keys: 'Esc', label: 'Close dialogs and overlays' },
]

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    tag === 'SELECT' ||
    target.isContentEditable
  )
}

export function useKeydown(handler: (e: KeyboardEvent) => void): void {
  const handlerRef = useRef(handler)
  useEffect(() => {
    handlerRef.current = handler
  }, [handler])
  useEffect(() => {
    const listener = (e: KeyboardEvent) => handlerRef.current(e)
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
  }, [])
}
