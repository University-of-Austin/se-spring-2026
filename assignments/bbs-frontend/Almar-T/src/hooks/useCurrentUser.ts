import { useCallback, useEffect, useState } from "react";

const KEY = "bbs:current-username";

// Each useCurrentUser() call creates a separate piece of useState.
// Without a notify channel they'd diverge after any setCurrentUser
// (the storage event only fires in *other* tabs, not the writer).
// A tiny module-level subscriber set fans out same-tab writes to
// every live hook instance.
const subscribers = new Set<(v: string | null) => void>();

function read(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function write(v: string | null): void {
  try {
    if (v) localStorage.setItem(KEY, v);
    else localStorage.removeItem(KEY);
  } catch {
    // Storage may throw in private mode — degrade to in-memory.
  }
}

export function useCurrentUser(): {
  currentUser: string | null;
  setCurrentUser: (u: string | null) => void;
} {
  const [user, setUser] = useState<string | null>(() => read());

  useEffect(() => {
    subscribers.add(setUser);
    // Cross-tab updates land here too.
    const onStorage = (e: StorageEvent) => {
      if (e.key === KEY) setUser(e.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => {
      subscribers.delete(setUser);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setCurrentUser = useCallback((u: string | null) => {
    write(u);
    subscribers.forEach((cb) => cb(u));
  }, []);

  return { currentUser: user, setCurrentUser };
}
