import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Theme = "light" | "dark" | "system";

const LS_KEY = "bbs.theme";
const VALID: Theme[] = ["light", "dark", "system"];

interface ThemeContextValue {
  theme: Theme;
  /** What's actually rendered right now (system mode resolves to one of these). */
  resolved: "light" | "dark";
  setTheme: (t: Theme) => void;
  /** Cycle through system → dark → light → system for header toggle. */
  cycle: () => void;
}

const Ctx = createContext<ThemeContextValue | null>(null);

function readInitial(): Theme {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw && (VALID as string[]).includes(raw)) return raw as Theme;
  } catch { /* private mode etc. */ }
  return "system";
}

function systemPrefersLight(): boolean {
  return typeof window !== "undefined"
    && window.matchMedia
    && window.matchMedia("(prefers-color-scheme: light)").matches;
}

function applyTheme(t: Theme): "light" | "dark" {
  const root = document.documentElement;
  if (t === "system") {
    root.removeAttribute("data-theme");
    return systemPrefersLight() ? "light" : "dark";
  }
  root.setAttribute("data-theme", t);
  return t;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Apply the initial theme to the DOM synchronously so the first paint
  // already matches the user's choice.
  const initial = readInitial();
  const [theme, setThemeState] = useState<Theme>(initial);
  const [resolved, setResolved] = useState<"light" | "dark">(() => applyTheme(initial));

  function setTheme(t: Theme) {
    try { localStorage.setItem(LS_KEY, t); } catch { /* ignore */ }
    setThemeState(t);
    setResolved(applyTheme(t));
  }

  function cycle() {
    const next: Theme = theme === "system" ? "dark" : theme === "dark" ? "light" : "system";
    setTheme(next);
  }

  // When in system mode, react to OS-level theme changes.
  useEffect(() => {
    if (theme !== "system") return;
    if (!window.matchMedia) return;
    const mql = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = (e: MediaQueryListEvent) => setResolved(e.matches ? "light" : "dark");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [theme]);

  return (
    <Ctx.Provider value={{ theme, resolved, setTheme, cycle }}>
      {children}
    </Ctx.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const c = useContext(Ctx);
  if (!c) throw new Error("useTheme must be used inside ThemeProvider");
  return c;
}
