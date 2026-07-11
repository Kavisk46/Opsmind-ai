import { create } from "zustand";

interface LoadingState {
  activeCount: number;
  isLoading: boolean;
  start: () => void;
  stop: () => void;
}

// Counter-based rather than a plain boolean: two concurrent async operations
// both toggling a boolean would let the first to finish hide the indicator
// while the second is still in flight.
export const useLoadingStore = create<LoadingState>((set) => ({
  activeCount: 0,
  isLoading: false,
  start: () =>
    set((state) => {
      const activeCount = state.activeCount + 1;
      return { activeCount, isLoading: activeCount > 0 };
    }),
  stop: () =>
    set((state) => {
      const activeCount = Math.max(0, state.activeCount - 1);
      return { activeCount, isLoading: activeCount > 0 };
    }),
}));
