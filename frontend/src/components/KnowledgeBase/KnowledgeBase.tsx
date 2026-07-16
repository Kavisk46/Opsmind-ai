"use client";

import { ChevronRight, Clock, FolderOpen, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import categoriesData from "@/lib/mock-data/kb-categories.json";
import documentsData from "@/lib/mock-data/kb-documents.json";
import foldersData from "@/lib/mock-data/kb-folders.json";
import tagsData from "@/lib/mock-data/kb-tags.json";
import { useModalStore } from "@/store/modal-store";

import { filterDocuments, sortDocuments } from "./document-filters";
import { DocumentGrid } from "./DocumentGrid";
import { DOCUMENT_VIEWER_MODAL_ID, DocumentViewer } from "./DocumentViewer";
import { EmptyState } from "./EmptyState";
import { FilterBar } from "./FilterBar";
import { getDescendantFolderIds, getFolderPath } from "./folder-tree";
import { FolderTree } from "./FolderTree";
import { useFavoritesStore } from "./store/favorites-store";
import { useRecentDocumentsStore } from "./store/recent-documents-store";
import type {
  Category,
  Document,
  Folder,
  SortOption,
  Tag,
  ViewMode,
} from "./types";
import { UploadModal } from "./UploadModal";
import { ViewTabs } from "./ViewTabs";

const folders = foldersData as Folder[];
const documents = documentsData as Document[];
const categories = categoriesData as Category[];
const tags = tagsData as Tag[];

export function KnowledgeBase() {
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [isFolderListOpen, setIsFolderListOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [sortOption, setSortOption] = useState<SortOption>("updated-desc");
  const [viewMode, setViewMode] = useState<ViewMode>("all");
  const isLoading = useSimulatedLoad();

  const favoriteIds = useFavoritesStore((state) => state.favoriteIds);
  const toggleFavorite = useFavoritesStore((state) => state.toggleFavorite);
  const recentIds = useRecentDocumentsStore((state) => state.recentIds);
  const recordView = useRecentDocumentsStore((state) => state.recordView);
  const openModal = useModalStore((state) => state.openModal);

  useEffect(() => {
    useFavoritesStore.persist.rehydrate();
    useRecentDocumentsStore.persist.rehydrate();
  }, []);

  const folderPath = useMemo(
    () => (selectedFolderId ? getFolderPath(folders, selectedFolderId) : []),
    [selectedFolderId]
  );

  const folderDescendantIds = useMemo(
    () =>
      selectedFolderId ? getDescendantFolderIds(folders, selectedFolderId) : null,
    [selectedFolderId]
  );

  const filtered = useMemo(
    () =>
      filterDocuments(documents, {
        query,
        categoryId,
        tagIds,
        folderDescendantIds,
        viewMode,
        favoriteIds,
        recentIds,
      }),
    [query, categoryId, tagIds, folderDescendantIds, viewMode, favoriteIds, recentIds]
  );

  // "Recent" is already in most-recently-viewed order from filterDocuments —
  // re-sorting it would defeat the point of that view.
  const results = viewMode === "recent" ? filtered : sortDocuments(filtered, sortOption);

  const hasActiveFilters =
    query.trim() !== "" || categoryId !== null || tagIds.length > 0;

  const handleClearFilters = () => {
    setQuery("");
    setCategoryId(null);
    setTagIds([]);
  };

  const handleSelectFolder = (folderId: string | null) => {
    setSelectedFolderId(folderId);
    setIsFolderListOpen(false);
  };

  const handleOpenDocument = (documentId: string) => {
    recordView(documentId);
    openModal(DOCUMENT_VIEWER_MODAL_ID, { documentId });
  };

  const activeFolderName = selectedFolderId
    ? (folderPath[folderPath.length - 1]?.name ?? "Folder")
    : "All Documents";

  const emptyState = (() => {
    if (viewMode === "favorites" && !hasActiveFilters && !selectedFolderId) {
      return (
        <EmptyState
          icon={Star}
          title="No favorites yet"
          description="Star a document to see it here."
        />
      );
    }
    if (viewMode === "recent" && !hasActiveFilters && !selectedFolderId) {
      return (
        <EmptyState
          icon={Clock}
          title="No recent documents"
          description="Documents you open will show up here."
        />
      );
    }
    return (
      <EmptyState
        title="No documents found"
        description="Try adjusting your search or filters."
        action={
          hasActiveFilters ? (
            <Button type="button" variant="outline" size="sm" onClick={handleClearFilters}>
              Clear filters
            </Button>
          ) : undefined
        }
      />
    );
  })();

  return (
    <>
      <div className="flex flex-col gap-4 lg:flex-row">
        <button
          type="button"
          onClick={() => setIsFolderListOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={isFolderListOpen}
          className="flex items-center gap-2 rounded-lg border border-border bg-card p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
        >
          <FolderOpen
            className="h-4 w-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <span className="truncate text-sm font-medium text-foreground">
            {activeFolderName}
          </span>
        </button>

        <div className="hidden lg:block">
          <FolderTree
            folders={folders}
            documents={documents}
            selectedFolderId={selectedFolderId}
            onSelectFolder={setSelectedFolderId}
          />
        </div>

        {isFolderListOpen && (
          <div
            className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80 lg:hidden"
            onClick={() => setIsFolderListOpen(false)}
            aria-hidden="true"
          />
        )}
        {isFolderListOpen && (
          <div className="fixed inset-x-4 top-20 bottom-4 z-(--z-modal) animate-scale-in motion-reduce:animate-none lg:hidden">
            <FolderTree
              folders={folders}
              documents={documents}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
              onClose={() => setIsFolderListOpen(false)}
            />
          </div>
        )}

        <div className="min-w-0 flex-1 space-y-4">
          {folderPath.length > 0 && (
            <nav
              aria-label="Folder path"
              className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground"
            >
              <button
                type="button"
                onClick={() => setSelectedFolderId(null)}
                className="rounded hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                All Documents
              </button>
              {folderPath.map((folder, index) => {
                const isLast = index === folderPath.length - 1;
                return (
                  <span key={folder.id} className="flex items-center gap-1.5">
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                    {isLast ? (
                      <span
                        className="font-medium text-foreground"
                        aria-current="page"
                      >
                        {folder.name}
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setSelectedFolderId(folder.id)}
                        className="rounded hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {folder.name}
                      </button>
                    )}
                  </span>
                );
              })}
            </nav>
          )}

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <ViewTabs
              value={viewMode}
              onChange={setViewMode}
              favoritesCount={favoriteIds.length}
              recentCount={recentIds.length}
              controls="kb-results"
            />
          </div>

          <FilterBar
            categories={categories}
            tags={tags}
            query={query}
            onQueryChange={setQuery}
            categoryId={categoryId}
            onCategoryChange={setCategoryId}
            tagIds={tagIds}
            onTagIdsChange={setTagIds}
            sortOption={sortOption}
            onSortChange={setSortOption}
            onClearFilters={handleClearFilters}
            hasActiveFilters={hasActiveFilters}
          />

          <p aria-live="polite" className="text-sm text-muted-foreground">
            {isLoading
              ? "Loading documents…"
              : `${results.length} ${results.length === 1 ? "document" : "documents"}`}
          </p>

          <div
            id="kb-results"
            role="tabpanel"
            aria-labelledby={`kb-tab-${viewMode}`}
          >
            <DocumentGrid
              documents={results}
              categories={categories}
              tags={tags}
              favoriteIds={favoriteIds}
              onToggleFavorite={toggleFavorite}
              onOpenDocument={handleOpenDocument}
              isLoading={isLoading}
              emptyState={emptyState}
            />
          </div>
        </div>
      </div>

      <DocumentViewer documents={documents} />
      <UploadModal />
    </>
  );
}
