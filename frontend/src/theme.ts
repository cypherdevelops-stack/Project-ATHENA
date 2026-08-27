export type Theme = 'light' | 'dark';

const THEME_KEY = 'athena.theme';

export function getTheme(): Theme {
  return localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark';
}

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  window.dispatchEvent(new CustomEvent<Theme>('athena-theme-change', { detail: theme }));
}

export function initializeTheme() {
  setTheme(getTheme());
}
