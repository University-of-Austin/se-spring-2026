// Theme toggle, matching kepano's stephango.com design exactly:
//   - 20×36px pill outline (just border, no fill)
//   - 18×18px icon directly inside, 1px from the appropriate edge
//   - Icon color = muted gray; turns accent (turquoise) on hover
//   - Sun icon (left) when light, moon icon (right) when dark
// Uses currentColor on the SVG so a single `text-muted group-hover:text-accent`
// chain controls the icon color without separate fill props.

import { useTheme } from '../context/useTheme'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light' : 'Switch to dark'}
      className="group inline-flex items-center h-5 w-9 rounded-full border border-border hover:border-accent transition-colors"
    >
      <span
        aria-hidden
        className={`block h-[18px] w-[18px] ml-px text-muted group-hover:text-accent transition-transform duration-100 ${
          isDark ? 'translate-x-4' : ''
        }`}
      >
        {isDark ? (
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-full w-full">
            <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-full w-full">
            <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
          </svg>
        )}
      </span>
    </button>
  )
}
