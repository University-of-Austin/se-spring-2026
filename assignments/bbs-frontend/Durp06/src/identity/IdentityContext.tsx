import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

const STORAGE_KEY = 'bbs:username';

interface IdentityValue {
  username: string | null;
  setUsername: (next: string | null) => void;
}

const IdentityCtx = createContext<IdentityValue | null>(null);

export function IdentityProvider({ children }: { children: ReactNode }) {
  // Initialiser reads from localStorage synchronously so the first render
  // already reflects the persisted user — no "logged-out flash" on refresh.
  const [username, setUsernameState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  const setUsername = useCallback((next: string | null) => {
    setUsernameState(next);
  }, []);

  useEffect(() => {
    try {
      if (username === null) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, username);
    } catch {
      // ignore quota / privacy-mode errors
    }
  }, [username]);

  return <IdentityCtx.Provider value={{ username, setUsername }}>{children}</IdentityCtx.Provider>;
}

export function useIdentity(): IdentityValue {
  const v = useContext(IdentityCtx);
  if (!v) throw new Error('useIdentity must be used inside <IdentityProvider>');
  return v;
}
