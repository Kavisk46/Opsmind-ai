import { create } from "zustand";
import { persist } from "zustand/middleware";

const MAX_RECENT = 8;

interface RecentDocumentsState {
  recentIds: string[];
  recordView: (documentId: string) => void;
}

// Starts empty, not seeded from mock data — same reasoning as
// favorites-store.ts: real, per-user browser-local state over real
// document ids, with nothing to pre-populate for a new account.
export const useRecentDocumentsStore = create<RecentDocumentsState>()(
  persist(
    (set) => ({
      recentIds: [],
      recordView: (documentId) =>
        set((state) => ({
          recentIds: [
            documentId,
            ...state.recentIds.filter((id) => id !== documentId),
          ].slice(0, MAX_RECENT),
        })),
    }),
    {
      name: "opsmind-kb-recent-documents",
      skipHydration: true,
    }
  )
);
