import { useQuery } from "@tanstack/react-query";

import { apiClient, type UploadOptions } from "@/lib/api";

// Wire shape verified directly against backend/schemas/document.py — never
// guessed. `status` is the document's ingestion pipeline stage (see
// backend/models/document.py's DocumentStatus enum: uploaded, processing,
// embedding, ready, or failed) — a DIFFERENT thing from an UploadEntry's
// own "uploading" | "success" | "error" in UploadItem.tsx, which is about
// the HTTP upload transaction, not what happens to the file afterward.
interface DocumentWire {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface UploadedDocument {
  id: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  status: string;
  errorMessage: string | null;
  createdAt: string;
}

function toUploadedDocument(document: DocumentWire): UploadedDocument {
  return {
    id: document.id,
    filename: document.filename,
    contentType: document.content_type,
    sizeBytes: document.size_bytes,
    status: document.status,
    errorMessage: document.error_message,
    createdAt: document.created_at,
  };
}

// POST /documents — multipart/form-data, verified against
// api/routes/documents.py's `upload_document(file: UploadFile, ...)`.
// Returns 202 Accepted with the created document row; background
// ingestion (chunking/embedding) happens after this resolves and isn't
// tracked here (see UploadedDocument.status's doc comment above — this
// app doesn't poll GET /documents/{id}/status for live ingestion progress,
// only shows whatever status came back with the upload/list response).
export function uploadDocument(
  file: File,
  options: UploadOptions = {}
): Promise<UploadedDocument> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  return apiClient
    .upload<DocumentWire>("/documents", formData, options)
    .then(toUploadedDocument);
}

// GET /documents — every document the current user owns. The backend's
// repository query (DocumentRepository.list_by_owner) has no ORDER BY, so
// row order isn't guaranteed — sorted here by created_at (newest first)
// rather than trusting whatever order the database happens to return.
export async function listDocuments(options?: {
  signal?: AbortSignal;
}): Promise<UploadedDocument[]> {
  const documents = await apiClient.get<DocumentWire[]>("/documents", {
    signal: options?.signal,
  });
  return documents
    .map(toUploadedDocument)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

// Shared React Query key — StatsCards.tsx (Dashboard) and UploadModal.tsx
// both need the real document list; using the same key means the second
// one to mount gets an instant cache hit instead of a redundant
// GET /documents, and invalidating this key after an upload/delete keeps
// BOTH in sync without either needing to know the other exists.
export const DOCUMENTS_QUERY_KEY = ["documents"] as const;

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: ({ signal }) => listDocuments({ signal }),
  });
}

// DELETE /documents/{id} — 204 No Content on success; a 404 (already
// deleted, or never belonged to this user) surfaces as a normal ApiError
// for the caller to handle like any other failed request.
export async function deleteDocument(
  documentId: string,
  options?: { signal?: AbortSignal }
): Promise<void> {
  await apiClient.delete<void>(`/documents/${documentId}`, {
    signal: options?.signal,
  });
}
