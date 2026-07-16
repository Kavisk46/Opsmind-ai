import { formatRelativeTime } from "@/components/ActivityList";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import { getFileTypeConfig } from "./file-type";
import type { Document } from "./types";

interface DocumentMetaProps {
  document: Pick<Document, "fileType" | "author" | "updatedAt">;
  className?: string;
}

// Reused by both DocumentCard and DocumentViewer so the two surfaces never
// drift out of sync on how a document's metadata is presented.
export function DocumentMeta({ document, className }: DocumentMetaProps) {
  const { icon: FileTypeIcon, label } = getFileTypeConfig(document.fileType);

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground",
        className
      )}
    >
      <span className="inline-flex items-center gap-1.5">
        <Avatar name={document.author} size={20} />
        {document.author}
      </span>
      <span>Updated {formatRelativeTime(document.updatedAt)}</span>
      <Badge variant="muted" className="gap-1">
        <FileTypeIcon className="h-3 w-3" aria-hidden="true" />
        {label}
      </Badge>
    </div>
  );
}
