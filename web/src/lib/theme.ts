export const CONTRAST_THEMES = ["dark", "light", "high"] as const;

export type ContrastTheme = (typeof CONTRAST_THEMES)[number];

export const THEME_STORAGE_KEY = "niveshguide-contrast";
export const THEME_EVENT = "niveshguide-theme";

export const THEME_OPTIONS: {
  id: ContrastTheme;
  label: string;
  hint: string;
}[] = [
  { id: "dark", label: "Dark", hint: "Home page look" },
  { id: "light", label: "Light", hint: "Brighter pages" },
  { id: "high", label: "High contrast", hint: "Stronger text and borders" },
];

export function isContrastTheme(value: string | null | undefined): value is ContrastTheme {
  return value === "dark" || value === "light" || value === "high";
}

export function readStoredTheme(): ContrastTheme {
  if (typeof window === "undefined") return "dark";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isContrastTheme(stored) ? stored : "dark";
  } catch {
    return "dark";
  }
}

export function applyContrastTheme(theme: ContrastTheme) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* ignore quota / private mode */
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}
