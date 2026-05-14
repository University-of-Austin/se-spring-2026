import { createContext, useCallback, useContext, useMemo, useState } from "react";

type Ctx = {
  username: string | null;
  setUsername: (u: string) => void;
  clearUsername: () => void;
};

const UserContext = createContext<Ctx | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(
    () => localStorage.getItem("username"),
  );

  const setUsername = useCallback((u: string) => {
    localStorage.setItem("username", u);
    setUsernameState(u);
  }, []);

  const clearUsername = useCallback(() => {
    localStorage.removeItem("username");
    setUsernameState(null);
  }, []);

  const value = useMemo(
    () => ({ username, setUsername, clearUsername }),
    [username, setUsername, clearUsername],
  );
  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useCurrentUser(): Ctx {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useCurrentUser must be used inside <UserProvider>");
  return ctx;
}
