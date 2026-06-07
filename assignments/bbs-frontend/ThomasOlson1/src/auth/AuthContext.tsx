import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

const STORAGE_KEY = "bbs.username";

type AuthValue = {
  username: string | null;
  setUsername: (u: string | null) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });

  useEffect(() => {
    if (username) localStorage.setItem(STORAGE_KEY, username);
    else localStorage.removeItem(STORAGE_KEY);
  }, [username]);

  // Keep tabs in sync if user switches in another tab
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setUsernameState(e.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setUsername = useCallback((u: string | null) => setUsernameState(u), []);
  const signOut = useCallback(() => setUsernameState(null), []);

  return (
    <AuthContext.Provider value={{ username, setUsername, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
