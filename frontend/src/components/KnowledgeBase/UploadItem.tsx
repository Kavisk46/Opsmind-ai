import { AlertCircle, Check, FileText, RotateCcw, Trash2, X } from "lucide-react";

import { Progress } from "@/components/ui/progress";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

export interface UploadEntry {
  id: string;
  filename: string;
  sizeBytes: number;
  // Present for a file actively selected in this session (needed to
  // retry-resend the same bytes); absent for an entry seeded from
  // GET /documents on modal open, which has no local file content, only
  // the backend's record of it.
  file: File | null;
  // The backend's real document id — set once an upload succeeds, or
  // immediately for a pre-existing document fetched via listDocuments().
  // null only while a brand-new upload is still in flight or has failed
  // before ever getting a response.
  documentId: string | null;
  status: "uploading" | "success" | "error";
  progress: number;
  errorMessage?: string;
}

interface UploadItemProps {
  entry: UploadEntry;
  onRemove: (id: string) => void;
  onRetry: (id: string) => void;
  onDelete: (id: string) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadItem({
  entry,
  onRemove,
  onRetry,
  onDelete,
}: UploadItemProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-border p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <FileText className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium text-foreground">
            {entry.filename}
          </p>
          <div className="flex shrink-0 items-center gap-1">
            {entry.status === "error" && entry.file && (
              <button
                type="button"
                onClick={() => onRetry(entry.id)}
                aria-label={`Retry uploading ${entry.filename}`}
                className={cn(
                  "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                  FOCUS_RING_CLASS
                )}
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
            {entry.status === "success" && entry.documentId && (
              <button
                type="button"
                onClick={() => onDelete(entry.id)}
                aria-label={`Delete ${entry.filename}`}
                className={cn(
                  "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-destructive",
                  FOCUS_RING_CLASS
                )}
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
            <button
              type="button"
              onClick={() => onRemove(entry.id)}
              aria-label={`Remove ${entry.filename}`}
              className={cn(
                "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                FOCUS_RING_CLASS
              )}
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {formatFileSize(entry.sizeBytes)}
        </p>

        {entry.status === "uploading" && (
          <Progress
            value={entry.progress}
            label={`Uploading ${entry.filename}`}
            className="mt-2"
          />
        )}
        {entry.status === "success" && (
          <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-success">
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            Uploaded
          </p>
        )}
        {entry.status === "error" && (
          <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {entry.errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
