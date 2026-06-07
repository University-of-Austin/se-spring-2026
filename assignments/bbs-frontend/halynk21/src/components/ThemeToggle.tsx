import { useTheme } from '../context/ThemeContext';

const ICON: Record<string, string> = {
  light: '☀',
  dark: '☾',
  system: '◐',
};

const NEXT_LABEL: Record<string, string> = {
  light: 'Switch to dark theme',
  dark: 'Switch to system theme',
  system: 'Switch to light theme',
};

export function ThemeToggle() {
  const { theme, cycle } = useTheme();
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={cycle}
      aria-label={NEXT_LABEL[theme]}
      title={`Theme: ${theme}`}
    >
      <span aria-hidden="true">{ICON[theme]}</span>
    </button>
  );
}
