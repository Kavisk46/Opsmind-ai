"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";
import { useModalStore } from "@/store/modal-store";

import { useDeleteDocument, useDocuments, useUploadDocument } from "./documents-api";
import { SearchBar } from "./SearchBar";
import {
  UPLOAD_ACCEPT_ATTRIBUTE,
  validateFile,
} from "./upload-validation";
import { UploadDropzone } from "./UploadDropzone";
import { UploadItem, type UploadEntry } from "./UploadItem";

export const UPLOAD_MODAL_ID = "kb-upload";

// Client-side only — GET /documents has no page/limit/offset params
// (verified: no such query params anywhere in api/routes/documents.py),
// so this paginates the already-fully-fetched real list in the UI rather
// than requesting pages from a backend that doesn't support them.
const PAGE_SIZE = 10;

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
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // Cached and SHARED with the Dashboard's StatsGrid "Documents" card (see
  // documents-api.ts) — useUploadDocument/useDeleteDocument below both
  // invalidate this same key on success, so the dashboard reflects it too
  // without needing to know this modal exists.
  const documentsQuery = useDocuments();
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

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

  // Seeds the list with documents already uploaded in earlier sessions —
  // this IS this feature's "document listing": the same UploadItem list
  // doubles as both "what I'm uploading right now" and "what I've already
  // uploaded" (INDEPENDENTLY mutable state after this — uploads/retries
  // mutate per-entry progress, which isn't something query data drives).
  // This component is fully unmounted/remounted each time the modal
  // closes/opens (see UploadModal above), so this mount-only effect
  // re-seeds fresh (from cache, if warm) on every open, same as before.
  useEffect(() => {
    if (documentsQuery.data) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEntries((prev) => [
        ...prev,
        ...documentsQuery.data.map(
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
    }
  }, [documentsQuery.data]);

  useEffect(() => {
    if (documentsQuery.error) {
      toast(getFriendlyErrorMessage(normalizeError(documentsQuery.error)));
    }
  }, [documentsQuery.error]);

  const runUpload = (entryId: string, file: File) => {
    const controller = new AbortController();
    abortControllersRef.current.set(entryId, controller);

    uploadMutation.mutate(
      {
        file,
        signal: controller.signal,
        onProgress: (percent) => {
          setEntries((prev) =>
            prev.map((existing) =>
              existing.id === entryId ? { ...existing, progress: percent } : existing
            )
          );
        },
      },
      {
        // useUploadDocument's own onSuccess already invalidates the
        // documents/stats query keys (shared with the Dashboard) — this
        // callback only updates THIS entry's local row state.
        onSuccess: (document) => {
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
        },
        onError: (error) => {
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
        },
        onSettled: () => {
          abortControllersRef.current.delete(entryId);
        },
      }
    );
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
    setPage(1);

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

    // Optimistic removal from THIS modal's own local row list — separate
    // from, and in addition to, useDeleteDocument's own optimistic update
    // of the shared documents/search query cache (see documents-api.ts).
    setEntries((prev) => prev.filter((existing) => existing.id !== id));

    deleteMutation.mutate(documentId, {
      onError: (error) => {
        toast(getFriendlyErrorMessage(normalizeError(error)));
        // Failed server-side — restore the entry rather than leaving the
        // UI claiming it's gone when it isn't.
        setEntries((prev) => [entry, ...prev]);
      },
    });
  };

  // Client-side filter over the real, already-fetched entries in THIS
  // modal's own upload/manage list — a real GET /documents/search endpoint
  // exists now (see the main page's search box, which uses it), but this
  // modal's search is over a small, already-in-memory set scoped to this
  // upload session, so filtering it locally avoids a redundant network
  // round trip for data already sitting in `entries`.
  const filteredEntries = entries.filter((entry) =>
    entry.filename.toLowerCase().includes(searchQuery.trim().toLowerCase())
  );
  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedEntries = filteredEntries.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setPage(1);
  };

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
          {documentsQuery.isPending && (
            <p className="text-xs text-muted-foreground">
              Loading your documents…
            </p>
          )}
          {entries.length > 0 && (
            <>
              <SearchBar value={searchQuery} onChange={handleSearchChange} />
              {filteredEntries.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No documents match &ldquo;{searchQuery}&rdquo;.
                </p>
              ) : (
                <>
                  <div className="space-y-2">
                    {pagedEntries.map((entry) => (
                      <UploadItem
                        key={entry.id}
                        entry={entry}
                        onRemove={handleRemove}
                        onRetry={handleRetry}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between gap-2 pt-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                      >
                        Previous
                      </Button>
                      <span className="text-xs text-muted-foreground">
                        Page {currentPage} of {totalPages}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setPage((p) => Math.min(totalPages, p + 1))
                        }
                        disabled={currentPage >= totalPages}
                      >
                        Next
                      </Button>
                    </div>
                  )}
                </>
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
