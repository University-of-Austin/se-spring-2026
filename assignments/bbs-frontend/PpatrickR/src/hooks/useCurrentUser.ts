import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "bbs.username";

function read(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function useCurrentUser() {
  const [username, setUsernameState] = useState<string | null>(() => read());

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) setUsernameState(e.newValue);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setUsername = useCallback((next: string) => {
    localStorage.setItem(STORAGE_KEY, next);
    setUsernameState(next);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUsernameState(null);
  }, []);

  return { username, setUsername, clear };
}
