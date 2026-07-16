"use client";

import { Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import { DocumentMeta } from "./DocumentMeta";
import { getFileTypeConfig } from "./file-type";
import type { Document } from "./types";

interface DocumentCardProps {
  document: Document;
  categoryName: string | undefined;
  tagNames: string[];
  isFavorite: boolean;
  onOpen: () => void;
  onToggleFavorite: () => void;
}

// Two sibling buttons rather than one big card-button with a nested
// favorite button — interactive content can't nest inside a <button> in
// valid HTML, so the favorite toggle is a separately-positioned sibling.
export function DocumentCard({
  document,
  categoryName,
  tagNames,
  isFavorite,
  onOpen,
  onToggleFavorite,
}: DocumentCardProps) {
  const { icon: FileTypeIcon } = getFileTypeConfig(document.fileType);

  return (
    <div className="relative flex flex-col rounded-lg border border-border bg-card shadow-card">
      <button
        type="button"
        onClick={onOpen}
        className="flex flex-1 flex-col gap-3 rounded-lg p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex items-start gap-3 pr-8">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <FileTypeIcon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground">
              {document.title}
            </h3>
            {categoryName && (
              <p className="truncate text-xs text-muted-foreground">
                {categoryName}
              </p>
            )}
          </div>
        </div>

        <p className="line-clamp-2 text-sm text-muted-foreground">
          {document.excerpt}
        </p>

        {tagNames.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tagNames.map((tagName) => (
              <Badge key={tagName} variant="muted">
                {tagName}
              </Badge>
            ))}
          </div>
        )}

        <DocumentMeta document={document} className="mt-auto pt-1" />
      </button>

      <button
        type="button"
        onClick={onToggleFavorite}
        aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
        aria-pressed={isFavorite}
        className={cn(
          "absolute top-3 right-3 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isFavorite && "text-warning"
        )}
      >
        <Star
          className={cn("h-4 w-4", isFavorite && "fill-current")}
          aria-hidden="true"
        />
      </button>
    </div>
  );
}
