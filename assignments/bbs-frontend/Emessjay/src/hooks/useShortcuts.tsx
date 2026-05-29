// Global keyboard shortcuts.
//
// Bindings:
//   ?         toggle help overlay
//   Escape    close help overlay
//   g f       go to feed
//   g c       go to compose
//   g u       go to users
//   g i       go to identity
//   n         new post (jump to compose)
//   /         focus the feed search input (when on feed)
//
// "g" is a leader key in the Gmail/GitHub tradition: press g then
// another key within ~1s.  We track this with a ref to a small bit
// of mutable state so re-renders don't reset it.
//
// We deliberately ignore shortcuts while the user is typing into an
// input/textarea/select/contenteditable element, except for "?",
// because keyboard shortcuts that fire while you're typing your post
// are infuriating.  "/" still focuses the search, even from outside
// the input.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { paths } from "../router/paths";

type Ctx = {
  helpOpen: boolean;
  toggleHelp: () => void;
  closeHelp: () => void;
  registerSearchFocus: (fn: (() => void) | null) => void;
};

const ShortcutsContext = createContext<Ctx | null>(null);

const LEADER_TIMEOUT_MS = 1000;

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

export function ShortcutsProvider({ children }: { children: ReactNode }) {
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();
  const leaderRef = useRef<{ active: boolean; expiresAt: number }>({
    active: false,
    expiresAt: 0,
  });
  // Pages register a "focus my search input" callback so "/" works
  // globally and dispatches to whatever's on screen.
  const searchFocusRef = useRef<(() => void) | null>(null);

  const closeHelp = useCallback(() => setHelpOpen(false), []);
  const toggleHelp = useCallback(() => setHelpOpen((o) => !o), []);

  const registerSearchFocus = useCallback((fn: (() => void) | null) => {
    searchFocusRef.current = fn;
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // "?" is allowed everywhere — it's the help shortcut.
      if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setHelpOpen((o) => !o);
        return;
      }
      if (e.key === "Escape" && helpOpen) {
        setHelpOpen(false);
        return;
      }

      // Everything below is ignored if the user is typing.
      if (isEditableTarget(e.target)) return;

      // Bare modifier-free keys only.
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const now = Date.now();
      const leaderActive = leaderRef.current.active && now < leaderRef.current.expiresAt;

      if (leaderActive) {
        leaderRef.current = { active: false, expiresAt: 0 };
        switch (e.key) {
          case "f": e.preventDefault(); navigate(paths.feed()); return;
          case "c": e.preventDefault(); navigate(paths.compose()); return;
          case "u": e.preventDefault(); navigate(paths.users()); return;
          case "i": e.preventDefault(); navigate(paths.identity()); return;
          default: return; // unknown leader combo — drop silently
        }
      }

      switch (e.key) {
        case "g":
          leaderRef.current = { active: true, expiresAt: now + LEADER_TIMEOUT_MS };
          return;
        case "n":
          e.preventDefault();
          navigate(paths.compose());
          return;
        case "/":
          if (searchFocusRef.current) {
            e.preventDefault();
            searchFocusRef.current();
          }
          return;
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate, helpOpen]);

  const value = useMemo<Ctx>(
    () => ({ helpOpen, toggleHelp, closeHelp, registerSearchFocus }),
    [helpOpen, toggleHelp, closeHelp, registerSearchFocus],
  );

  return <ShortcutsContext.Provider value={value}>{children}</ShortcutsContext.Provider>;
}

export function useShortcuts(): Ctx {
  const ctx = useContext(ShortcutsContext);
  if (!ctx) throw new Error("useShortcuts must be used inside <ShortcutsProvider>");
  return ctx;
}
