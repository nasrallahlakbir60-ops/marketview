import { create } from "zustand";

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "marketview-theme";

function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Stockage indisponible (navigation privée...) : thème par défaut.
  }
  return "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#101713" : "#f4f6f2");
}

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: readStoredTheme(),
  toggleTheme: () => {
    const theme: Theme = get().theme === "dark" ? "light" : "dark";
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Préférence non mémorisée, sans conséquence.
    }
    applyTheme(theme);
    set({ theme });
  },
}));
