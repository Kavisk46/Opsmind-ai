"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";

import { MarkdownRenderer } from "@/components/Markdown";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";
import { useModalStore } from "@/store/modal-store";

import { DocumentMeta } from "./DocumentMeta";
import { getFileTypeConfig } from "./file-type";
import type { Document } from "./types";

export const DOCUMENT_VIEWER_MODAL_ID = "kb-document-viewer";

interface DocumentViewerProps {
  documents: Document[];
}

// Modal driven entirely by the shared, previously-unused `useModalStore` —
// any other feature can reuse the same store instead of building its own.
export function DocumentViewer({ documents }: DocumentViewerProps) {
  const activeModalId = useModalStore((state) => state.activeModalId);
  const modalProps = useModalStore((state) => state.modalProps);
  const closeModal = useModalStore((state) => state.closeModal);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const isOpen = activeModalId === DOCUMENT_VIEWER_MODAL_ID;
  const documentId =
    isOpen && typeof modalProps?.documentId === "string"
      ? modalProps.documentId
      : undefined;
  const activeDocument = documentId
    ? documents.find((document) => document.id === documentId)
    : undefined;

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    closeButtonRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeModal();
      }
    }
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, closeModal]);

  if (!isOpen || !activeDocument) {
    return null;
  }

  return (
    <>
      <div
        className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80"
        onClick={closeModal}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={activeDocument.title}
        className="fixed inset-4 z-(--z-modal) mx-auto flex max-w-[1600px] flex-col overflow-hidden rounded-lg border border-border bg-card shadow-modal animate-scale-in motion-reduce:animate-none sm:inset-x-8 sm:inset-y-10 lg:inset-x-24 lg:inset-y-12"
      >
        <div className="flex items-start justify-between gap-4 border-b border-border p-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-foreground">
              {activeDocument.title}
            </h2>
            <DocumentMeta document={activeDocument} className="mt-1.5" />
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={closeModal}
            aria-label="Close document"
            className={cn(
              "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
              FOCUS_RING_CLASS
            )}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {activeDocument.fileType === "markdown" && activeDocument.content ? (
            <MarkdownRenderer content={activeDocument.content} />
          ) : activeDocument.fileType === "image" &&
            activeDocument.previewImageUrl ? (
            // Preview URL is arbitrary/mock document data, not a known static
            // asset — next/image requires an allowlisted domain.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={activeDocument.previewImageUrl}
              alt={activeDocument.title}
              className="max-w-full rounded-md border border-border"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <p className="text-sm font-medium text-foreground">
                Preview not available
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                This is a mock {getFileTypeConfig(activeDocument.fileType).label.toLowerCase()}{" "}
                file — there&apos;s no real file behind it to preview or
                download.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
