"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { MarkdownRenderer } from "@/components/Markdown";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient, getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";
import { useModalStore } from "@/store/modal-store";

import { DocumentMeta } from "./DocumentMeta";
import { downloadDocument } from "./documents-api";
import { getFileTypeConfig } from "./file-type";
import type { Document } from "./types";

export const DOCUMENT_VIEWER_MODAL_ID = "kb-document-viewer";

interface DocumentViewerProps {
  documents: Document[];
  onDeleteDocument: (documentId: string, title: string) => void;
}

type PreviewContent = { kind: "text"; text: string } | { kind: "blob"; blob: Blob };

function renderCsvPreview(text: string) {
  const rows = text.trim().split("\n").map((line) => line.split(","));
  const [header, ...body] = rows;
  if (!header) {
    return null;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {header.map((cell, index) => (
            <TableHead key={index}>{cell.trim()}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {body.map((row, rowIndex) => (
          <TableRow key={rowIndex}>
            {row.map((cell, cellIndex) => (
              <TableCell key={cellIndex}>{cell.trim()}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// Modal driven entirely by the shared, previously-unused `useModalStore` —
// any other feature can reuse the same store instead of building its own.
export function DocumentViewer({ documents, onDeleteDocument }: DocumentViewerProps) {
  const activeModalId = useModalStore((state) => state.activeModalId);
  const modalProps = useModalStore((state) => state.modalProps);
  const closeModal = useModalStore((state) => state.closeModal);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const isOpen = activeModalId === DOCUMENT_VIEWER_MODAL_ID;
  const documentId =
    isOpen && typeof modalProps?.documentId === "string"
      ? modalProps.documentId
      : undefined;
  // Deliberately re-looked-up from the live `documents` list every render
  // rather than snapshotted once on open — an optimistic delete (see
  // documents-api.ts's useDeleteDocument) removes the entry from that
  // list immediately, which this lookup then reflects as `undefined`,
  // which the early return below turns into the modal closing itself —
  // no separate "close on delete" wiring needed.
  const activeDocument = documentId
    ? documents.find((document) => document.id === documentId)
    : undefined;

  // "doc" (.docx) has no preview path at all — query stays disabled for
  // it, so renderPreview() below shows "No preview available" without
  // ever making a request.
  const previewEligible = Boolean(activeDocument) && activeDocument?.fileType !== "doc";

  // Fetches the real file bytes for a supported preview type the moment a
  // document opens — nothing is pre-loaded on the Document object (no
  // backend field for it), so this is a genuine on-demand fetch through
  // apiClient.getBlob(), not a read from static data. useQuery (rather
  // than manual useState/useEffect) is what gives this loading/error
  // states for free with no setState call anywhere in an effect body —
  // and keyed by document id, so reopening a previously-viewed document
  // in the same session shows its preview instantly from cache.
  const previewQuery = useQuery({
    queryKey: ["document-preview", activeDocument?.id],
    queryFn: async (): Promise<PreviewContent> => {
      if (!activeDocument) {
        throw new Error("No active document");
      }
      const blob = await apiClient.getBlob(
        `/documents/download/${activeDocument.id}`
      );
      if (activeDocument.fileType === "image" || activeDocument.fileType === "pdf") {
        return { kind: "blob", blob };
      }
      return { kind: "text", text: await blob.text() };
    },
    enabled: previewEligible,
  });

  // The one genuine side effect here — a real browser resource that must
  // be released. Derived via useMemo so a new object URL is only ever
  // created when the underlying blob actually changes; released in this
  // effect's cleanup, never through a setState call.
  const objectUrl = useMemo(() => {
    if (previewQuery.data?.kind === "blob") {
      return URL.createObjectURL(previewQuery.data.blob);
    }
    return null;
  }, [previewQuery.data]);

  useEffect(() => {
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [objectUrl]);

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

  const renderPreview = () => {
    if (!previewEligible) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <p className="text-sm font-medium text-foreground">
            No preview available
          </p>
          <p className="max-w-xs text-xs text-muted-foreground">
            {getFileTypeConfig(activeDocument.fileType).label} files can&apos;t
            be previewed here yet — download it to view the contents.
          </p>
        </div>
      );
    }
    if (previewQuery.isPending) {
      return (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-muted-foreground">Loading preview…</p>
        </div>
      );
    }
    if (previewQuery.error) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <p className="text-sm font-medium text-foreground">
            Couldn&apos;t load preview
          </p>
          <p className="max-w-xs text-xs text-muted-foreground">
            {getFriendlyErrorMessage(normalizeError(previewQuery.error))}
          </p>
        </div>
      );
    }
    if (previewQuery.data.kind === "blob" && objectUrl) {
      if (activeDocument.fileType === "image") {
        return (
          // eslint-disable-next-line @next/next/no-img-element -- object URL, not a static/remote asset next/image can optimize
          <img
            src={objectUrl}
            alt={activeDocument.title}
            className="mx-auto max-w-full rounded-md border border-border"
          />
        );
      }
      return (
        <iframe
          src={objectUrl}
          title={activeDocument.title}
          className="h-full w-full rounded-md border border-border"
        />
      );
    }
    if (previewQuery.data.kind === "text") {
      if (activeDocument.fileType === "markdown") {
        return <MarkdownRenderer content={previewQuery.data.text} />;
      }
      if (activeDocument.fileType === "csv") {
        return renderCsvPreview(previewQuery.data.text);
      }
      return (
        <pre className="whitespace-pre-wrap text-sm text-foreground">
          {previewQuery.data.text}
        </pre>
      );
    }
    return null;
  };

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
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => downloadDocument(activeDocument.id)}
              aria-label={`Download ${activeDocument.title}`}
              className={cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                FOCUS_RING_CLASS
              )}
            >
              <Download className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() =>
                onDeleteDocument(activeDocument.id, activeDocument.title)
              }
              aria-label={`Delete ${activeDocument.title}`}
              className={cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-destructive",
                FOCUS_RING_CLASS
              )}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              ref={closeButtonRef}
              type="button"
              onClick={closeModal}
              aria-label="Close document"
              className={cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                FOCUS_RING_CLASS
              )}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">{renderPreview()}</div>
      </div>
    </>
  );
}
