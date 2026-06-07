// Shared "currently acting as" username, backed by localStorage.
// Lives in React Context so SignIn's setUsername immediately updates
// Layout's view (otherwise each component's local useState would only
// see its own copy, and the Layout redirect-effect would race).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { clearStoredUsername, getStoredUsername, setStoredUsername } from "../lib/username";

interface UsernameContextValue {
  username: string | null;
  setUsername: (name: string) => void;
  clearUsername: () => void;
}

const UsernameContext = createContext<UsernameContextValue | null>(null);

export function UsernameProvider({ children }: { children: ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(() => getStoredUsername());

  // Other tabs may change the stored username; keep this tab in sync.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "bbs.username") setUsernameState(e.newValue);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setUsername = useCallback((name: string) => {
    setStoredUsername(name);
    setUsernameState(name);
  }, []);

  const clearUsername = useCallback(() => {
    clearStoredUsername();
    setUsernameState(null);
  }, []);

  return (
    <UsernameContext.Provider value={{ username, setUsername, clearUsername }}>
      {children}
    </UsernameContext.Provider>
  );
}

export function useUsername() {
  const ctx = useContext(UsernameContext);
  if (!ctx) throw new Error("useUsername must be used inside a UsernameProvider");
  return ctx;
}
