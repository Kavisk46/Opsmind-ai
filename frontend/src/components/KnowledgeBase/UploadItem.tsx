import { AlertCircle, Check, FileText, X } from "lucide-react";

import { Progress } from "@/components/ui/progress";

export interface UploadEntry {
  id: string;
  file: File;
  status: "uploading" | "success" | "error";
  progress: number;
  errorMessage?: string;
}

interface UploadItemProps {
  entry: UploadEntry;
  onRemove: (id: string) => void;
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

export function UploadItem({ entry, onRemove }: UploadItemProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-border p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <FileText className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium text-foreground">
            {entry.file.name}
          </p>
          <button
            type="button"
            onClick={() => onRemove(entry.id)}
            aria-label={`Remove ${entry.file.name}`}
            className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground">
          {formatFileSize(entry.file.size)}
        </p>

        {entry.status === "uploading" && (
          <Progress
            value={entry.progress}
            label={`Uploading ${entry.file.name}`}
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
