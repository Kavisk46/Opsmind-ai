import { create } from "zustand";
import { persist } from "zustand/middleware";

import recentDocumentsData from "@/lib/mock-data/kb-recent-documents.json";

const MAX_RECENT = 8;

interface RecentDocumentsState {
  recentIds: string[];
  recordView: (documentId: string) => void;
}

export const useRecentDocumentsStore = create<RecentDocumentsState>()(
  persist(
    (set) => ({
      recentIds: recentDocumentsData as string[],
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
