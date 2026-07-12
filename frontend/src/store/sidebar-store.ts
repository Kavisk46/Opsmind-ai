import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SidebarState {
  isOpen: boolean;
  isCollapsed: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isOpen: false,
      isCollapsed: false,
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      toggle: () => set((state) => ({ isOpen: !state.isOpen })),
      setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
      toggleCollapsed: () =>
        set((state) => ({ isCollapsed: !state.isCollapsed })),
    }),
    {
      name: "opsmind-sidebar",
      // Only the collapsed preference persists — isOpen (the mobile drawer)
      // must always start closed on a fresh load.
      partialize: (state) => ({ isCollapsed: state.isCollapsed }),
      // Auto-hydration reads localStorage before React's hydration
      // comparison runs, which would make the client's first render
      // diverge from the server-rendered (always-expanded) markup — a real
      // mismatch, not a cosmetic one. Skipping it and rehydrating
      // explicitly after mount (see Sidebar's effect) keeps first paint
      // matching the server; the persisted preference applies a moment
      // later instead.
      skipHydration: true,
    }
  )
);
