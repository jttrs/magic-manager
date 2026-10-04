// Theme: follows the OS (prefers-color-scheme) unless the user overrides it.
// The override lives in localStorage and is reflected as <html data-theme>.
export type ThemePref = 'system' | 'light' | 'dark';
const KEY = 'mm.theme';

export function readTheme(): ThemePref {
  const v = localStorage.getItem(KEY);
  return v === 'light' || v === 'dark' ? v : 'system';
}

export function applyTheme(pref: ThemePref): void {
  const root = document.documentElement;
  if (pref === 'system') {
    root.removeAttribute('data-theme');
    localStorage.removeItem(KEY);
  } else {
    root.setAttribute('data-theme', pref);
    localStorage.setItem(KEY, pref);
  }
}
