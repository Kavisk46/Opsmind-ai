import { create } from "zustand";
import { persist } from "zustand/middleware";

import favoritesData from "@/lib/mock-data/kb-favorites.json";

interface FavoritesState {
  favoriteIds: string[];
  toggleFavorite: (documentId: string) => void;
  isFavorite: (documentId: string) => boolean;
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favoriteIds: favoritesData as string[],
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
