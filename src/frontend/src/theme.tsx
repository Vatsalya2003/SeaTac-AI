import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export type Theme = 'light' | 'dark';
const THEME_KEY = 'seatac_theme';
// keep in step with the inline script in index.html, which applies the theme before the first paint

const systemTheme = (): Theme => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

const storedTheme = (): Theme | null => {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
};

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.classList.toggle('dark', theme === 'dark');  // also switches the shadcn/ui colour variables in index.css
  root.style.colorScheme = theme;
}

/** Light or dark: the saved choice, otherwise the system setting (followed live until the user picks one). */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => storedTheme() ?? systemTheme());

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const follow = () => { if (!storedTheme()) setTheme(query.matches ? 'dark' : 'light'); };
    query.addEventListener('change', follow);
    return () => query.removeEventListener('change', follow);
  }, []);

  const toggleTheme = () => setTheme((current) => {
    const next: Theme = current === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, next); } catch { /* not saved */ }
    return next;
  });

  return { theme, toggleTheme };
}

export function ThemeToggle({ theme, onToggle, className = '' }: { theme: Theme; onToggle: () => void; className?: string }) {
  const dark = theme === 'dark';
  const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
  return (
    <button type="button" className={`sea-icon-btn ${className}`.trim()} onClick={onToggle}
            aria-label={label} title={label} data-testid="theme-toggle">
      {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </button>
  );
}
