import { useEffect } from "react";

export type Shortcut = {
  key: string;
  ctrlOrMeta?: boolean;
  // Whether to fire even when the user is typing in an input/textarea.
  // Default is false — most shortcuts shouldn't steal keys mid-type.
  allowInInput?: boolean;
  handler: (e: KeyboardEvent) => void;
};

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return el.isContentEditable;
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      for (const s of shortcuts) {
        const modOk = s.ctrlOrMeta ? e.ctrlKey || e.metaKey : true;
        if (!modOk) continue;
        if (e.key !== s.key) continue;
        if (!s.allowInInput && isTypingTarget(e.target)) continue;
        s.handler(e);
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shortcuts]);
}
