import { useCallback, useEffect, useState } from "react";

const KEY = "bbs:theme";
export type Theme = "light" | "dark";

function read(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

function systemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function apply(theme: Theme | null): void {
  const root = document.documentElement;
  if (theme) root.setAttribute("data-theme", theme);
  else root.removeAttribute("data-theme");
}

export function useTheme(): {
  theme: Theme;
  /** true if user has explicitly set a theme; false if following system */
  explicit: boolean;
  toggle: () => void;
} {
  const [stored, setStored] = useState<Theme | null>(() => read());
  const [system, setSystem] = useState<Theme>(() => systemTheme());

  // Apply on mount + whenever stored changes.
  useEffect(() => {
    apply(stored);
  }, [stored]);

  // Watch for system theme changes while user is on default.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) =>
      setSystem(e.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const theme: Theme = stored ?? system;

  const toggle = useCallback(() => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* ignore */
    }
    setStored(next);
  }, [theme]);

  return { theme, explicit: stored !== null, toggle };
}
