import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api";

import {
  DOCUMENTS_QUERY_KEY,
  DOCUMENT_STATS_QUERY_KEY,
  useDeleteDocument,
  useDocumentStats,
  useSearchDocuments,
  useUploadDocument,
  type UploadedDocument,
} from "./documents-api";

vi.mock("@/lib/api", () => ({
  apiClient: {
    get: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
    getBaseUrl: vi.fn(() => "https://api.example.com"),
  },
}));

const mockedApiClient = vi.mocked(apiClient, { deep: true });

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

const wireDocument = {
  id: "doc-1",
  filename: "notes.txt",
  content_type: "text/plain",
  size_bytes: 10,
  status: "ready",
  error_message: null,
  created_at: "2026-07-28T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useSearchDocuments", () => {
  it("exposes the mapped search results", async () => {
    mockedApiClient.get.mockResolvedValue([wireDocument]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useSearchDocuments({ q: "notes" }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([
      {
        id: "doc-1",
        filename: "notes.txt",
        contentType: "text/plain",
        sizeBytes: 10,
        status: "ready",
        errorMessage: null,
        createdAt: "2026-07-28T00:00:00Z",
      },
    ]);
  });
});

describe("useDocumentStats", () => {
  it("exposes the mapped stats", async () => {
    mockedApiClient.get.mockResolvedValue({
      total_documents: 3,
      total_storage_bytes: 900,
      documents_by_type: { "text/plain": 3 },
      recent_uploads: [wireDocument],
    });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useDocumentStats(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.totalDocuments).toBe(3);
    expect(result.current.data?.recentUploads).toHaveLength(1);
  });
});

describe("useUploadDocument", () => {
  it("invalidates the documents list and stats after a successful upload", async () => {
    mockedApiClient.upload.mockResolvedValue(wireDocument);
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUploadDocument(), { wrapper });
    result.current.mutate({ file: new File(["a"], "notes.txt") });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(DOCUMENTS_QUERY_KEY);
    expect(invalidatedKeys).toContainEqual(DOCUMENT_STATS_QUERY_KEY);
  });
});

describe("useDeleteDocument", () => {
  it("optimistically removes the document from cached lists", async () => {
    const { queryClient, wrapper } = makeWrapper();
    const existing: UploadedDocument[] = [
      { ...wireDocument, id: "doc-1" },
      { ...wireDocument, id: "doc-2" },
    ].map((d) => ({
      id: d.id,
      filename: d.filename,
      contentType: d.content_type,
      sizeBytes: d.size_bytes,
      status: d.status,
      errorMessage: d.error_message,
      createdAt: d.created_at,
    }));
    queryClient.setQueryData(DOCUMENTS_QUERY_KEY, existing);
    let resolveDelete!: () => void;
    mockedApiClient.delete.mockReturnValue(
      new Promise((resolve) => {
        resolveDelete = () => resolve(undefined);
      })
    );

    const { result } = renderHook(() => useDeleteDocument(), { wrapper });
    result.current.mutate("doc-1");

    await waitFor(() =>
      expect(
        queryClient.getQueryData<UploadedDocument[]>(DOCUMENTS_QUERY_KEY)
      ).toEqual([existing[1]])
    );

    resolveDelete();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("rolls back the optimistic removal if the delete request fails", async () => {
    const { queryClient, wrapper } = makeWrapper();
    const existing: UploadedDocument[] = [
      {
        id: "doc-1",
        filename: "notes.txt",
        contentType: "text/plain",
        sizeBytes: 10,
        status: "ready",
        errorMessage: null,
        createdAt: "2026-07-28T00:00:00Z",
      },
    ];
    queryClient.setQueryData(DOCUMENTS_QUERY_KEY, existing);
    mockedApiClient.delete.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useDeleteDocument(), { wrapper });
    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(
      queryClient.getQueryData<UploadedDocument[]>(DOCUMENTS_QUERY_KEY)
    ).toEqual(existing);
  });
});
