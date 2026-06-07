import { useEffect } from "react";

type Modifier = "mod" | "shift" | "alt";

export type Shortcut = {
  key: string;
  modifiers?: Modifier[];
  handler: (e: KeyboardEvent) => void;
  /** if true, fires even when focus is in an input/textarea */
  whenTyping?: boolean;
};

function matches(e: KeyboardEvent, s: Shortcut): boolean {
  if (e.key.toLowerCase() !== s.key.toLowerCase()) return false;
  const mods = s.modifiers ?? [];
  const wantMod = mods.includes("mod");
  const wantShift = mods.includes("shift");
  const wantAlt = mods.includes("alt");
  const hasMod = e.metaKey || e.ctrlKey;
  if (wantMod !== hasMod) return false;
  if (wantShift !== e.shiftKey) return false;
  if (wantAlt !== e.altKey) return false;
  return true;
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable
  );
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      for (const s of shortcuts) {
        if (!matches(e, s)) continue;
        if (!s.whenTyping && isTyping(e.target)) continue;
        e.preventDefault();
        s.handler(e);
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shortcuts]);
}
