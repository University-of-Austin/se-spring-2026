// localStorage-backed "which username am I posting as" state.
//
// X-Username isn't auth — it's a header the client claims.  We're
// storing a preference: which name to attach to the next POST.
// localStorage survives refresh and tab close; that's the only
// requirement.  Not surviving incognito or "clear site data" is fine.
//
// Provided as a Context so views don't need to prop-drill the value.
// useCurrentUser() reads it; setCurrentUser() writes to localStorage
// AND to React state so every consumer re-renders.

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const STORAGE_KEY = "bbs.username";

type CurrentUserContextValue = {
  username: string | null;
  setUsername: (name: string | null) => void;
};

const CurrentUserContext = createContext<CurrentUserContextValue | null>(null);

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  // Lazy initializer: read localStorage exactly once on mount.
  const [username, setUsernameState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  // Mirror state back to localStorage whenever it changes.  Doing this
  // in an effect (rather than inside setUsername) keeps the in-React
  // value authoritative even if a write to localStorage throws (e.g.
  // quota exceeded, private mode in some old browsers).
  useEffect(() => {
    try {
      if (username === null) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, username);
    } catch {
      // Ignore: we keep the in-memory state regardless.
    }
  }, [username]);

  const value = useMemo<CurrentUserContextValue>(
    () => ({ username, setUsername: setUsernameState }),
    [username],
  );

  return <CurrentUserContext.Provider value={value}>{children}</CurrentUserContext.Provider>;
}

export function useCurrentUser(): CurrentUserContextValue {
  const ctx = useContext(CurrentUserContext);
  if (!ctx) throw new Error("useCurrentUser must be used inside <CurrentUserProvider>");
  return ctx;
}
