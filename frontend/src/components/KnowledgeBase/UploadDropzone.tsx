"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
}

// Generic drag-and-drop + file-picker surface — takes no knowledge of what
// happens to the files afterward, so it's reusable anywhere a drop target
// is needed, not just here.
export function UploadDropzone({
  onFilesSelected,
  accept,
  multiple = true,
  disabled = false,
}: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(false);
    if (disabled) {
      return;
    }
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!disabled) {
      setIsDragActive(true);
    }
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (files.length > 0) {
      onFilesSelected(files);
    }
    // Reset so selecting the same file again still fires a change event.
    event.target.value = "";
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragActive(false)}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
        isDragActive ? "border-primary bg-accent" : "border-border",
        disabled && "pointer-events-none opacity-50"
      )}
    >
      <UploadCloud
        className="h-8 w-8 text-muted-foreground"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-foreground">
        Drag and drop files here, or{" "}
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          className={cn(
            "rounded text-primary underline underline-offset-2 hover:no-underline",
            FOCUS_RING_CLASS
          )}
        >
          browse
        </button>
      </p>
      <p className="text-xs text-muted-foreground">
        Markdown, PDF, Word, Excel, PowerPoint, or images — up to 20 MB each.
      </p>
      <label className="sr-only" htmlFor="kb-upload-input">
        Choose files to upload
      </label>
      <input
        id="kb-upload-input"
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleInputChange}
        className="sr-only"
      />
    </div>
  );
}
