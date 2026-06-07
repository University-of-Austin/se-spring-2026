import { useCallback, useEffect, useState } from "react";

/**
 * Per-user, client-only board mute list. Boards added here are hidden from
 * the main feed but stay visible when explicitly browsed via the Boards
 * page or a /?board= URL.
 *
 * Lives in localStorage under "bbs.blocked-boards" as a JSON array of
 * board names. Cross-component sync is done via a custom DOM event so
 * multiple hooks in the same tab stay in step without a context provider.
 */

const LS_KEY = "bbs.blocked-boards";
const EVENT = "bbs:blocked-boards-changed";

function readSet(): Set<string> {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return new Set(parsed.filter((s): s is string => typeof s === "string"));
    }
    return new Set();
  } catch {
    return new Set();
  }
}

function writeSet(set: Set<string>) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify([...set]));
  } catch { /* ignore quota / privacy */ }
  window.dispatchEvent(new Event(EVENT));
}

export function useBlockedBoards() {
  const [blocked, setBlocked] = useState<Set<string>>(readSet);

  useEffect(() => {
    const handler = () => setBlocked(readSet());
    window.addEventListener(EVENT, handler);
    // Also pick up changes from other tabs.
    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_KEY) setBlocked(readSet());
    };
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(EVENT, handler);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const block = useCallback((board: string) => {
    const b = board.trim().toLowerCase();
    if (!b) return;
    const next = new Set(readSet());
    next.add(b);
    writeSet(next);
  }, []);

  const unblock = useCallback((board: string) => {
    const b = board.trim().toLowerCase();
    const next = new Set(readSet());
    next.delete(b);
    writeSet(next);
  }, []);

  const isBlocked = useCallback((board: string) => {
    return blocked.has(board.trim().toLowerCase());
  }, [blocked]);

  return { blocked, isBlocked, block, unblock };
}
