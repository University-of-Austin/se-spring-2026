import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";

interface AuthState {
  username: string | null;
  token: string | null;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setIdentity: (s: AuthState) => void;  // for tests / manual switch
}

const AuthContext = createContext<AuthContextValue | null>(null);

const LS_USERNAME = "bbs.username";
const LS_TOKEN = "bbs.token";

function readInitial(): AuthState {
  try {
    return {
      username: localStorage.getItem(LS_USERNAME),
      token: localStorage.getItem(LS_TOKEN),
    };
  } catch {
    return { username: null, token: null };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(readInitial);

  useEffect(() => {
    try {
      if (state.username) localStorage.setItem(LS_USERNAME, state.username);
      else localStorage.removeItem(LS_USERNAME);
      if (state.token) localStorage.setItem(LS_TOKEN, state.token);
      else localStorage.removeItem(LS_TOKEN);
    } catch { /* ignore quota / privacy mode */ }
  }, [state.username, state.token]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    setState({ username: res.username, token: res.token });
  }, []);

  const signup = useCallback(async (username: string, password: string) => {
    await api.signup(username, password);
    // Sign-up doesn't return a token; log them in immediately.
    const res = await api.login(username, password);
    setState({ username: res.username, token: res.token });
  }, []);

  const logout = useCallback(async () => {
    const token = state.token;
    setState({ username: null, token: null });
    if (token) {
      try { await api.logout(token); } catch { /* best-effort */ }
    }
  }, [state.token]);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout, setIdentity: setState }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
