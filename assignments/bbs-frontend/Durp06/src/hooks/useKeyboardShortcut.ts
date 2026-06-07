import { useEffect } from 'react';

interface ShortcutOptions {
  /** Match Ctrl on Windows/Linux OR Cmd (Meta) on Mac. */
  modifier?: 'ctrlOrMeta' | 'none';
  /** If true, fire even when focus is on an input/textarea/contenteditable. */
  whenInInput?: boolean;
}

function isTypingTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false;
  if (t.isContentEditable) return true;
  const tag = t.tagName.toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select';
}

// Tiny shortcut helper. Centralised so all components share the same
// "is the user typing right now?" suppression — otherwise `n` and `?` would
// fire while typing into the compose textarea, which is awful.
export function useKeyboardShortcut(
  key: string,
  handler: (e: KeyboardEvent) => void,
  { modifier = 'none', whenInInput = false }: ShortcutOptions = {},
) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (modifier === 'ctrlOrMeta' && !(e.ctrlKey || e.metaKey)) return;
      if (modifier === 'none' && (e.ctrlKey || e.metaKey || e.altKey)) return;
      if (e.key !== key) return;
      if (!whenInInput && isTypingTarget(e.target)) return;
      handler(e);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [key, handler, modifier, whenInInput]);
}
