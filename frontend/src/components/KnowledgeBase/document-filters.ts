import type { Document, SortOption, ViewMode } from "./types";

export const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "updated-desc", label: "Last updated (newest)" },
  { value: "updated-asc", label: "Last updated (oldest)" },
  { value: "title-asc", label: "Title (A–Z)" },
  { value: "title-desc", label: "Title (Z–A)" },
];

export interface FilterDocumentsOptions {
  query: string;
  categoryId: string | null;
  tagIds: string[];
  // Precomputed by the caller via getDescendantFolderIds — null means "no
  // folder selected, don't filter by folder".
  folderDescendantIds: string[] | null;
  viewMode: ViewMode;
  favoriteIds: string[];
  recentIds: string[];
}

export function filterDocuments(
  documents: Document[],
  options: FilterDocumentsOptions
): Document[] {
  const byId = new Map(documents.map((document) => [document.id, document]));

  // "Recent" is inherently order-significant (most-recently-viewed first),
  // so it seeds the working set in that order rather than filtering the
  // default array — everything else still filters on top of it normally.
  const base =
    options.viewMode === "recent"
      ? options.recentIds
          .map((id) => byId.get(id))
          .filter((document): document is Document => document !== undefined)
      : documents;

  const normalizedQuery = options.query.trim().toLowerCase();
  const favoriteSet = new Set(options.favoriteIds);

  return base.filter((document) => {
    if (options.viewMode === "favorites" && !favoriteSet.has(document.id)) {
      return false;
    }
    if (
      options.folderDescendantIds &&
      !options.folderDescendantIds.includes(document.folderId)
    ) {
      return false;
    }
    if (options.categoryId && document.categoryId !== options.categoryId) {
      return false;
    }
    if (
      options.tagIds.length > 0 &&
      !document.tagIds.some((tagId) => options.tagIds.includes(tagId))
    ) {
      return false;
    }
    if (normalizedQuery) {
      const haystack = `${document.title} ${document.excerpt}`.toLowerCase();
      if (!haystack.includes(normalizedQuery)) {
        return false;
      }
    }
    return true;
  });
}

export function sortDocuments(
  documents: Document[],
  sortOption: SortOption
): Document[] {
  const sorted = [...documents];

  switch (sortOption) {
    case "updated-desc":
      sorted.sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
      break;
    case "updated-asc":
      sorted.sort(
        (a, b) => new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
      );
      break;
    case "title-asc":
      sorted.sort((a, b) => a.title.localeCompare(b.title));
      break;
    case "title-desc":
      sorted.sort((a, b) => b.title.localeCompare(a.title));
      break;
  }

  return sorted;
}
