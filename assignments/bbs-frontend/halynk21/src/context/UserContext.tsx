import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as storage from '../lib/storage';

const USER_KEY = 'username';

type UserContextValue = {
  username: string | null;
  setUsername: (u: string | null) => void;
};

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(() => storage.get(USER_KEY));

  // Cross-tab sync. If another tab signs in/out, this tab follows.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== storage.fullKey(USER_KEY)) return;
      setUsernameState(e.newValue);
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setUsername = useCallback((u: string | null) => {
    if (u) storage.set(USER_KEY, u);
    else storage.remove(USER_KEY);
    setUsernameState(u);
  }, []);

  return (
    <UserContext.Provider value={{ username, setUsername }}>
      {children}
    </UserContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCurrentUser(): UserContextValue {
  const v = useContext(UserContext);
  if (!v) throw new Error('useCurrentUser must be used inside <UserProvider>');
  return v;
}
