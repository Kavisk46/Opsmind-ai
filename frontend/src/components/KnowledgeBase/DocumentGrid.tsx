import type { ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { DocumentCard } from "./DocumentCard";
import type { Category, Document, Tag } from "./types";

interface DocumentGridProps {
  documents: Document[];
  categories: Category[];
  tags: Tag[];
  favoriteIds: string[];
  onToggleFavorite: (documentId: string) => void;
  onOpenDocument: (documentId: string) => void;
  isLoading: boolean;
  emptyState: ReactNode;
}

function DocumentCardSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading document"
      className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4"
    >
      <div className="flex items-start gap-3">
        <Skeleton className="h-9 w-9 shrink-0 rounded-md" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-2/3" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

export function DocumentGrid({
  documents,
  categories,
  tags,
  favoriteIds,
  onToggleFavorite,
  onOpenDocument,
  isLoading,
  emptyState,
}: DocumentGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <DocumentCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return <>{emptyState}</>;
  }

  const categoryNameById = new Map(
    categories.map((category) => [category.id, category.name])
  );
  const tagNameById = new Map(tags.map((tag) => [tag.id, tag.name]));
  const favoriteSet = new Set(favoriteIds);

  return (
    <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {documents.map((document) => (
        <li key={document.id}>
          <DocumentCard
            document={document}
            categoryName={categoryNameById.get(document.categoryId)}
            tagNames={document.tagIds
              .map((tagId) => tagNameById.get(tagId))
              .filter((name): name is string => name !== undefined)}
            isFavorite={favoriteSet.has(document.id)}
            onOpen={() => onOpenDocument(document.id)}
            onToggleFavorite={() => onToggleFavorite(document.id)}
          />
        </li>
      ))}
    </ul>
  );
}
