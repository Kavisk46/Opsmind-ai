import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FavoritesState {
  favoriteIds: string[];
  toggleFavorite: (documentId: string) => void;
  isFavorite: (documentId: string) => boolean;
}

// Starts empty, not seeded from mock data — this is real, per-user
// browser-local state layered on top of real document ids (see
// documents-api.ts); there's no such thing as a "pre-existing favorite"
// for a brand new real account.
export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favoriteIds: [],
      toggleFavorite: (documentId) =>
        set((state) => ({
          favoriteIds: state.favoriteIds.includes(documentId)
            ? state.favoriteIds.filter((id) => id !== documentId)
            : [...state.favoriteIds, documentId],
        })),
      isFavorite: (documentId) => get().favoriteIds.includes(documentId),
    }),
    {
      name: "opsmind-kb-favorites",
      // See sidebar-store.ts for why this is skipped and rehydrated
      // explicitly after mount instead — avoids an SSR/client markup
      // mismatch on first paint.
      skipHydration: true,
    }
  )
);
