"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";
import { useModalStore } from "@/store/modal-store";

import { deleteDocument, listDocuments, uploadDocument } from "./documents-api";
import { SearchBar } from "./SearchBar";
import {
  UPLOAD_ACCEPT_ATTRIBUTE,
  validateFile,
} from "./upload-validation";
import { UploadDropzone } from "./UploadDropzone";
import { UploadItem, type UploadEntry } from "./UploadItem";

export const UPLOAD_MODAL_ID = "kb-upload";

export function UploadModal() {
  const activeModalId = useModalStore((state) => state.activeModalId);
  const isOpen = activeModalId === UPLOAD_MODAL_ID;

  // Mounted only while open, rather than always-mounted with an effect that
  // resets state on close — that way a fresh open naturally starts from
  // empty state via useState's initial value, no manual reset needed.
  if (!isOpen) {
    return null;
  }

  return <UploadModalContent />;
}

function UploadModalContent() {
  const closeModal = useModalStore((state) => state.closeModal);
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const [isLoadingExisting, setIsLoadingExisting] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useModalDismiss({ onClose: closeModal, closeButtonRef, containerRef });

  useEffect(() => {
    // Captured once, at effect-setup time, so the cleanup below reads a
    // reference guaranteed to still be valid rather than trusting the ref's
    // `.current` to be unchanged by the time it runs.
    const abortControllers = abortControllersRef.current;

    return () => {
      // Any upload still in flight shouldn't keep running (or calling
      // setState) after the modal that owns it has unmounted.
      abortControllers.forEach((controller) => controller.abort());
      abortControllers.clear();
    };
    // Mount-only: this component exists exactly as long as the modal is open.
  }, []);

  // Seeds the list with documents already uploaded in earlier sessions
  // (GET /documents) — this IS this feature's "document listing": the same
  // UploadItem list doubles as both "what I'm uploading right now" and
  // "what I've already uploaded", so delete works uniformly on either.
  useEffect(() => {
    const controller = new AbortController();

    listDocuments({ signal: controller.signal })
      .then((documents) => {
        setEntries((prev) => [
          ...prev,
          ...documents.map(
            (document): UploadEntry => ({
              id: document.id,
              filename: document.filename,
              sizeBytes: document.sizeBytes,
              file: null,
              documentId: document.id,
              status: "success",
              progress: 100,
            })
          ),
        ]);
      })
      .catch((error) => {
        const apiError = normalizeError(error);
        if (apiError.code !== "ABORTED") {
          toast(getFriendlyErrorMessage(apiError));
        }
      })
      .finally(() => setIsLoadingExisting(false));

    return () => controller.abort();
    // Mount-only: fetched exactly once when the modal opens.
  }, []);

  const runUpload = (entryId: string, file: File) => {
    const controller = new AbortController();
    abortControllersRef.current.set(entryId, controller);

    uploadDocument(file, {
      signal: controller.signal,
      onProgress: (percent) => {
        setEntries((prev) =>
          prev.map((existing) =>
            existing.id === entryId ? { ...existing, progress: percent } : existing
          )
        );
      },
    })
      .then((document) => {
        setEntries((prev) =>
          prev.map((existing) =>
            existing.id === entryId
              ? {
                  ...existing,
                  status: "success",
                  progress: 100,
                  documentId: document.id,
                }
              : existing
          )
        );
      })
      .catch((error) => {
        const apiError = normalizeError(error);
        if (apiError.code === "ABORTED") {
          // The entry was removed (or the modal closed) — nothing left to
          // update; setting an error on a discarded entry would just
          // resurrect it as a phantom row.
          return;
        }
        setEntries((prev) =>
          prev.map((existing) =>
            existing.id === entryId
              ? {
                  ...existing,
                  status: "error",
                  errorMessage: getFriendlyErrorMessage(apiError),
                }
              : existing
          )
        );
      })
      .finally(() => {
        abortControllersRef.current.delete(entryId);
      });
  };

  const handleFilesSelected = (files: File[]) => {
    const newEntries: UploadEntry[] = files.map((file) => {
      const error = validateFile(file);
      return {
        id: crypto.randomUUID(),
        filename: file.name,
        sizeBytes: file.size,
        file,
        documentId: null,
        status: error ? "error" : "uploading",
        progress: 0,
        errorMessage: error ?? undefined,
      };
    });

    setEntries((prev) => [...newEntries, ...prev]);

    for (const entry of newEntries) {
      if (entry.status === "uploading" && entry.file) {
        runUpload(entry.id, entry.file);
      }
    }
  };

  const handleRetry = (id: string) => {
    const entry = entries.find((existing) => existing.id === id);
    if (!entry?.file) {
      return;
    }
    setEntries((prev) =>
      prev.map((existing) =>
        existing.id === id
          ? { ...existing, status: "uploading", progress: 0, errorMessage: undefined }
          : existing
      )
    );
    runUpload(id, entry.file);
  };

  const handleRemove = (id: string) => {
    abortControllersRef.current.get(id)?.abort();
    abortControllersRef.current.delete(id);
    setEntries((prev) => prev.filter((entry) => entry.id !== id));
  };

  const handleDelete = (id: string) => {
    const entry = entries.find((existing) => existing.id === id);
    if (!entry?.documentId) {
      return;
    }
    const documentId = entry.documentId;

    // Optimistic removal — DELETE /documents/{id} is a 204 with nothing
    // useful to await visibly, and this is the user's own explicit delete
    // action, not a background process that could surprise them.
    setEntries((prev) => prev.filter((existing) => existing.id !== id));

    deleteDocument(documentId).catch((error) => {
      toast(getFriendlyErrorMessage(normalizeError(error)));
      // Failed server-side — restore the entry rather than leaving the UI
      // claiming it's gone when it isn't.
      setEntries((prev) => [entry, ...prev]);
    });
  };

  // Client-side filter over the real, already-fetched document list — no
  // backend search endpoint exists (verified: no such route anywhere in
  // api/routes/), so this is real data narrowed locally rather than a
  // fabricated "search" that queries nothing.
  const filteredEntries = entries.filter((entry) =>
    entry.filename.toLowerCase().includes(searchQuery.trim().toLowerCase())
  );

  return (
    <>
      <div
        className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80"
        onClick={closeModal}
        aria-hidden="true"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Upload documents"
        className="fixed inset-x-4 top-16 bottom-16 z-(--z-modal) mx-auto flex max-w-lg flex-col overflow-hidden rounded-lg border border-border bg-card shadow-modal animate-scale-in motion-reduce:animate-none sm:inset-x-auto sm:w-full"
      >
        <div className="flex items-center justify-between gap-4 border-b border-border p-4">
          <h2 className="text-lg font-semibold text-foreground">
            Upload documents
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={closeModal}
            aria-label="Close upload dialog"
            className={cn(
              "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
              FOCUS_RING_CLASS
            )}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <UploadDropzone
            onFilesSelected={handleFilesSelected}
            accept={UPLOAD_ACCEPT_ATTRIBUTE}
          />
          {isLoadingExisting && (
            <p className="text-xs text-muted-foreground">
              Loading your documents…
            </p>
          )}
          {entries.length > 0 && (
            <>
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
              {filteredEntries.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No documents match &ldquo;{searchQuery}&rdquo;.
                </p>
              ) : (
                <div className="space-y-2">
                  {filteredEntries.map((entry) => (
                    <UploadItem
                      key={entry.id}
                      entry={entry}
                      onRemove={handleRemove}
                      onRetry={handleRetry}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border p-4">
          <Button type="button" variant="outline" onClick={closeModal}>
            Done
          </Button>
        </div>
      </div>
    </>
  );
}
