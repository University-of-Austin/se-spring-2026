import { useCallback, useEffect, useSyncExternalStore } from "react";

const KEY = "bbs.username";
const EVENT = "bbs:user-changed";

function read(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function subscribe(cb: () => void) {
  // The 'storage' event fires across tabs; 'bbs:user-changed' is our
  // in-tab signal because storage events don't fire in the writing tab.
  window.addEventListener("storage", cb);
  window.addEventListener(EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(EVENT, cb);
  };
}

export function useUser(): {
  username: string | null;
  setUsername: (name: string | null) => void;
  signOut: () => void;
} {
  const username = useSyncExternalStore(subscribe, read, read);

  const setUsername = useCallback((name: string | null) => {
    try {
      if (name === null) localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, name);
    } catch {
      // localStorage can be unavailable (Safari private mode, etc).
      // The app degrades to "username resets every refresh" — fine.
    }
    window.dispatchEvent(new Event(EVENT));
  }, []);

  const signOut = useCallback(() => setUsername(null), [setUsername]);

  // No-op effect to keep the export shape simple; kept here for future
  // hooks that want to react to mount.
  useEffect(() => {}, []);

  return { username, setUsername, signOut };
}
