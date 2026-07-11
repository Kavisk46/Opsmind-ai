import { create } from "zustand";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

// Independent state container for theme *intent*. `next-themes` (see
// components/Providers/ThemeProvider.tsx) remains the source of truth for
// what's actually applied to the DOM, persisted, and resolved from system
// preference — this store does not duplicate that. Syncing the two is a
// deliberate follow-up integration, not done automatically here.
export const useThemeStore = create<ThemeState>((set) => ({
  mode: "system",
  setMode: (mode) => set({ mode }),
}));
