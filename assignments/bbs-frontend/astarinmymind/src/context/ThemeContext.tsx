// Provider for two-state dark mode (Gold B).
// On first visit, defaults to the OS preference via `prefers-color-scheme`.
// Once the user toggles, that pick is persisted in localStorage and locks in
// (we stop following OS changes — they made an explicit choice).
//
// The Context object + consumer hook live in ./useTheme so this file stays
// components-only and fast-refresh stays granular.

import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { ThemeContext } from './useTheme'
import type { Theme } from './useTheme'

function getInitialTheme(): Theme {
  // localStorage pick wins.
  const stored = localStorage.getItem('theme-pref')
  if (stored === 'light' || stored === 'dark') return stored
  // No pick yet → follow the OS preference.
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  // Sync the resolved theme to a class on <html> so CSS variables in `.dark` activate.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  // Follow OS preference changes ONLY if the user hasn't manually picked yet.
  useEffect(() => {
    if (localStorage.getItem('theme-pref')) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e: MediaQueryListEvent) => setThemeState(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const setTheme = (t: Theme) => {
    setThemeState(t)
    localStorage.setItem('theme-pref', t)
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
