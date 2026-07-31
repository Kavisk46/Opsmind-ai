import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiClient, type UploadOptions } from "@/lib/api";
import { formatFileSize } from "@/lib/format";

import { contentTypeToFileType } from "./file-type";
import type { Document as KbDocument } from "./types";

// Wire shapes the backend actually returns — verified directly against
// backend/schemas/document.py and backend/schemas/user.py before writing
// this file, never guessed. Kept as separate, minimal interfaces here
// (not shared with the backend repo) since this is the ONE place in the
// frontend that needs to know the raw wire format; everything else in
// this app works with the app-level `AuthUser` shape below.
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

// --- upload / list / delete (real endpoints, verified: api/routes/documents.py) ---

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
export const DOCUMENT_STATS_QUERY_KEY = ["documents", "stats"] as const;

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

// --- search (real endpoint, verified: api/routes/documents.py's /search) ---

export type SortOption = "newest" | "oldest" | "largest" | "smallest";

export interface SearchDocumentsParams {
  q?: string;
  contentType?: string;
  sort?: SortOption;
}

function searchDocumentsQueryKey(params: SearchDocumentsParams) {
  return ["documents", "search", params] as const;
}

// GET /documents/search — filename substring match (q), exact content-type
// filter, and server-side sort. Query params only included when actually
// set, so an empty search collapses to the same request GET /documents
// would make (matching backend behavior: all params are optional there).
export async function searchDocuments(
  params: SearchDocumentsParams = {},
  options?: { signal?: AbortSignal }
): Promise<UploadedDocument[]> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.contentType) {
    query.set("content_type", params.contentType);
  }
  if (params.sort) {
    query.set("sort", params.sort);
  }
  const queryString = query.toString();

  const documents = await apiClient.get<DocumentWire[]>(
    `/documents/search${queryString ? `?${queryString}` : ""}`,
    { signal: options?.signal }
  );
  return documents.map(toUploadedDocument);
}

export function useSearchDocuments(params: SearchDocumentsParams = {}) {
  return useQuery({
    queryKey: searchDocumentsQueryKey(params),
    queryFn: ({ signal }) => searchDocuments(params, { signal }),
    // Keeps the previous result set visible while a new debounced query is
    // in flight, instead of flashing the loading skeleton on every
    // keystroke — see KnowledgeBase.tsx's use of useDebouncedValue.
    placeholderData: keepPreviousData,
  });
}

// --- stats (real endpoint, verified: api/routes/documents.py's /stats) ---

interface DocumentStatsWire {
  total_documents: number;
  total_storage_bytes: number;
  documents_by_type: Record<string, number>;
  recent_uploads: DocumentWire[];
}

export interface DocumentStats {
  totalDocuments: number;
  totalStorageBytes: number;
  documentsByType: Record<string, number>;
  recentUploads: UploadedDocument[];
}

export async function getDocumentStats(options?: {
  signal?: AbortSignal;
}): Promise<DocumentStats> {
  const stats = await apiClient.get<DocumentStatsWire>("/documents/stats", {
    signal: options?.signal,
  });
  return {
    totalDocuments: stats.total_documents,
    totalStorageBytes: stats.total_storage_bytes,
    documentsByType: stats.documents_by_type,
    recentUploads: stats.recent_uploads.map(toUploadedDocument),
  };
}

export function useDocumentStats() {
  return useQuery({
    queryKey: DOCUMENT_STATS_QUERY_KEY,
    queryFn: ({ signal }) => getDocumentStats({ signal }),
  });
}

// --- download (real endpoint, verified: api/routes/documents.py's /download/{id}) ---

// Deliberately NOT a fetch()/apiClient call — GET /documents/download/{id}
// sets Content-Disposition: attachment (see that route), which is what
// makes a normal browser request download the file with the SERVER's own
// filename rather than rendering or navigating to it. The real httpOnly
// auth cookies (SameSite=None; Secure — see backend/core/cookies.py) are
// attached to this exactly like any other same-browser request, entirely
// independent of fetch()/CORS credentials — the same reasoning
// getGoogleLoginUrl() etc. already document for "this has to be a real
// browser-driven request, never a fetch()/XHR".
export function downloadDocument(documentId: string): void {
  const anchor = window.document.createElement("a");
  anchor.href = `${apiClient.getBaseUrl()}/documents/download/${documentId}`;
  anchor.rel = "noopener";
  window.document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

// --- mutations ---

interface UploadDocumentVariables {
  file: File;
  signal?: AbortSignal;
  onProgress?: (percent: number) => void;
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: UploadDocumentVariables) =>
      uploadDocument(variables.file, {
        signal: variables.signal,
        onProgress: variables.onProgress,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      void queryClient.invalidateQueries({
        queryKey: DOCUMENT_STATS_QUERY_KEY,
      });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(documentId),
    // Optimistic: a delete is easy to reverse (restore the cached
    // snapshot) and low-risk, unlike upload — which already has real
    // progress reporting and nothing meaningful to fake optimistically
    // ahead of a real server response. ["documents"] is a shared PREFIX
    // across the plain list, every search variant, AND the stats query
    // (a plain object, not a list) — Array.isArray guards against trying
    // to .filter() that one.
    onMutate: async (documentId: string) => {
      await queryClient.cancelQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      const previousLists = queryClient.getQueriesData<UploadedDocument[]>({
        queryKey: DOCUMENTS_QUERY_KEY,
      });
      previousLists.forEach(([key, data]) => {
        if (Array.isArray(data)) {
          queryClient.setQueryData(
            key,
            data.filter((document) => document.id !== documentId)
          );
        }
      });
      return { previousLists };
    },
    onError: (_error, _documentId, context) => {
      context?.previousLists.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      void queryClient.invalidateQueries({
        queryKey: DOCUMENT_STATS_QUERY_KEY,
      });
    },
  });
}

// --- KnowledgeBase UI adapter ---

function statusExcerpt(status: string): string {
  switch (status) {
    case "ready":
      return "Ready — fully indexed and searchable.";
    case "processing":
      return "Processing — extracting content…";
    case "embedding":
      return "Generating embeddings…";
    case "failed":
      return "Processing failed — this file couldn't be indexed.";
    default:
      return "Uploaded.";
  }
}

// Adapts a real document onto components/KnowledgeBase's existing
// (originally mock-only) Document shape, so DocumentCard/DocumentGrid/
// DocumentViewer don't need their own prop types rewritten. Folders,
// categories, and tags have no backend equivalent yet — every UI piece
// that reads them (FolderTree, CategoryFilter, TagFilter) already
// renders a correct, honest empty/unfiltered state when given nothing to
// group by, rather than this adapter fabricating folders that don't
// exist. `excerpt` becomes the document's real processing status instead
// of a fake generated summary; `author` is the real signed-in user's
// name (every listed document already belongs only to them — GET
// /documents/GET /documents/search only ever return the current owner's
// own rows).
export function toKbDocument(
  document: UploadedDocument,
  authorName: string
): KbDocument {
  return {
    id: document.id,
    title: document.filename,
    folderId: "",
    categoryId: "",
    tagIds: [],
    fileType: contentTypeToFileType(document.contentType),
    author: authorName,
    updatedAt: document.createdAt,
    sizeLabel: formatFileSize(document.sizeBytes),
    excerpt: statusExcerpt(document.status),
  };
}
