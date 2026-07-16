"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { useModalStore } from "@/store/modal-store";

import {
  UPLOAD_ACCEPT_ATTRIBUTE,
  simulateUpload,
  validateFile,
} from "./upload-simulation";
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
  const cancelFnsRef = useRef<Map<string, () => void>>(new Map());
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useModalDismiss({ onClose: closeModal, closeButtonRef, containerRef });

  useEffect(() => {
    // Captured once, at effect-setup time, so the cleanup below reads a
    // reference guaranteed to still be valid rather than trusting the ref's
    // `.current` to be unchanged by the time it runs.
    const cancelFns = cancelFnsRef.current;

    return () => {
      // Any simulated uploads still in flight shouldn't keep ticking (and
      // calling setState) after the modal that owns them has unmounted.
      cancelFns.forEach((cancel) => cancel());
      cancelFns.clear();
    };
    // Mount-only: this component exists exactly as long as the modal is open.
  }, []);

  const handleFilesSelected = (files: File[]) => {
    const newEntries: UploadEntry[] = files.map((file) => {
      const error = validateFile(file);
      return {
        id: crypto.randomUUID(),
        file,
        status: error ? "error" : "uploading",
        progress: 0,
        errorMessage: error ?? undefined,
      };
    });

    setEntries((prev) => [...newEntries, ...prev]);

    for (const entry of newEntries) {
      if (entry.status !== "uploading") {
        continue;
      }

      const { promise, cancel } = simulateUpload((percent) => {
        setEntries((prev) =>
          prev.map((existing) =>
            existing.id === entry.id
              ? { ...existing, progress: percent }
              : existing
          )
        );
      });
      cancelFnsRef.current.set(entry.id, cancel);

      promise.then(() => {
        setEntries((prev) =>
          prev.map((existing) =>
            existing.id === entry.id
              ? { ...existing, status: "success", progress: 100 }
              : existing
          )
        );
        cancelFnsRef.current.delete(entry.id);
      });
    }
  };

  const handleRemove = (id: string) => {
    cancelFnsRef.current.get(id)?.();
    cancelFnsRef.current.delete(id);
    setEntries((prev) => prev.filter((entry) => entry.id !== id));
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
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <UploadDropzone
            onFilesSelected={handleFilesSelected}
            accept={UPLOAD_ACCEPT_ATTRIBUTE}
          />
          {entries.length > 0 && (
            <div className="space-y-2">
              {entries.map((entry) => (
                <UploadItem
                  key={entry.id}
                  entry={entry}
                  onRemove={handleRemove}
                />
              ))}
            </div>
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
