// Context object + consumer hook for the theme (light/dark).
// Lives in a non-JSX file so that ThemeContext.tsx (the Provider component)
// can stay components-only for fast-refresh granularity.

import { createContext, useContext } from 'react'

export type Theme = 'light' | 'dark'

export type ThemeContextValue = {
  theme: Theme
  setTheme: (t: Theme) => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}
