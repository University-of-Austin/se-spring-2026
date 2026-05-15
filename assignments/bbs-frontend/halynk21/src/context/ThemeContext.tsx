import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as storage from '../lib/storage';

export type Theme = 'light' | 'dark' | 'system';

const THEME_KEY = 'theme';

type ThemeContextValue = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  cycle: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readSavedTheme(): Theme {
  const v = storage.get(THEME_KEY);
  if (v === 'light' || v === 'dark' || v === 'system') return v;
  return 'system';
}

// Apply theme to <html>: light/dark set data-theme, system removes it.
// Mirrors what the FOUC inline script does for the initial render.
function applyTheme(t: Theme): void {
  const root = document.documentElement;
  if (t === 'system') {
    root.removeAttribute('data-theme');
  } else {
    root.setAttribute('data-theme', t);
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readSavedTheme);

  // Apply on every change. (Initial mount mirrors what the inline FOUC
  // script already did, which is fine — setAttribute is idempotent.)
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Cross-tab sync: another tab changes the theme, we update too.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== storage.fullKey(THEME_KEY)) return;
      const next = readSavedTheme();
      setThemeState(next);
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    storage.set(THEME_KEY, t);
    setThemeState(t);
  }, []);

  const cycle = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light');
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, cycle }}>
      {children}
    </ThemeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const v = useContext(ThemeContext);
  if (!v) throw new Error('useTheme must be used inside <ThemeProvider>');
  return v;
}
