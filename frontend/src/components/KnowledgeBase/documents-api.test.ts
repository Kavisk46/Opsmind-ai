import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api";

import {
  deleteDocument,
  downloadDocument,
  getDocumentStats,
  listDocuments,
  searchDocuments,
  toKbDocument,
  uploadDocument,
  type UploadedDocument,
} from "./documents-api";

// The real ApiClient does real network I/O (fetch/XHR) — every test here
// mocks just the four methods documents-api.ts actually calls, so these
// tests exercise the wire<->app mapping and request-shape logic in this
// file, not the HTTP layer itself (already covered by client.ts's own
// concerns).
vi.mock("@/lib/api", () => ({
  apiClient: {
    get: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
    getBaseUrl: vi.fn(() => "https://api.example.com"),
  },
}));

const mockedApiClient = vi.mocked(apiClient, { deep: true });

beforeEach(() => {
  vi.clearAllMocks();
});

describe("uploadDocument", () => {
  it("sends the file as multipart form data to POST /documents", async () => {
    mockedApiClient.upload.mockResolvedValue({
      id: "doc-1",
      filename: "notes.txt",
      content_type: "text/plain",
      size_bytes: 11,
      status: "uploaded",
      error_message: null,
      created_at: "2026-07-28T00:00:00Z",
    });
    const file = new File(["hello world"], "notes.txt", { type: "text/plain" });

    const result = await uploadDocument(file);

    expect(mockedApiClient.upload).toHaveBeenCalledTimes(1);
    const [path, formData] = mockedApiClient.upload.mock.calls[0]!;
    expect(path).toBe("/documents");
    expect((formData as FormData).get("file")).toStrictEqual(file);
    expect(result).toEqual({
      id: "doc-1",
      filename: "notes.txt",
      contentType: "text/plain",
      sizeBytes: 11,
      status: "uploaded",
      errorMessage: null,
      createdAt: "2026-07-28T00:00:00Z",
    });
  });

  it("forwards signal/onProgress through to apiClient.upload", async () => {
    mockedApiClient.upload.mockResolvedValue({
      id: "doc-1",
      filename: "a.txt",
      content_type: "text/plain",
      size_bytes: 1,
      status: "uploaded",
      error_message: null,
      created_at: "2026-07-28T00:00:00Z",
    });
    const onProgress = vi.fn();
    const controller = new AbortController();

    await uploadDocument(new File(["a"], "a.txt"), {
      signal: controller.signal,
      onProgress,
    });

    const options = mockedApiClient.upload.mock.calls[0]![2];
    expect(options?.signal).toBe(controller.signal);
    expect(options?.onProgress).toBe(onProgress);
  });
});

describe("listDocuments", () => {
  it("maps and sorts documents newest-first by created_at", async () => {
    mockedApiClient.get.mockResolvedValue([
      {
        id: "old",
        filename: "old.txt",
        content_type: "text/plain",
        size_bytes: 1,
        status: "ready",
        error_message: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "new",
        filename: "new.txt",
        content_type: "text/plain",
        size_bytes: 1,
        status: "ready",
        error_message: null,
        created_at: "2026-06-01T00:00:00Z",
      },
    ]);

    const result = await listDocuments();

    expect(mockedApiClient.get).toHaveBeenCalledWith("/documents", {
      signal: undefined,
    });
    expect(result.map((d) => d.id)).toEqual(["new", "old"]);
  });
});

describe("deleteDocument", () => {
  it("calls DELETE /documents/{id}", async () => {
    mockedApiClient.delete.mockResolvedValue(undefined);

    await deleteDocument("doc-42");

    expect(mockedApiClient.delete).toHaveBeenCalledWith("/documents/doc-42", {
      signal: undefined,
    });
  });
});

describe("searchDocuments", () => {
  beforeEach(() => {
    mockedApiClient.get.mockResolvedValue([]);
  });

  it("requests GET /documents/search with no query string when no params are set", async () => {
    await searchDocuments();
    expect(mockedApiClient.get).toHaveBeenCalledWith(
      "/documents/search",
      expect.anything()
    );
  });

  it("includes q, content_type, and sort only when provided", async () => {
    await searchDocuments({ q: "report", contentType: "application/pdf", sort: "largest" });

    const [path] = mockedApiClient.get.mock.calls[0]!;
    const url = new URL(path as string, "https://example.com");
    expect(url.pathname).toBe("/documents/search");
    expect(url.searchParams.get("q")).toBe("report");
    expect(url.searchParams.get("content_type")).toBe("application/pdf");
    expect(url.searchParams.get("sort")).toBe("largest");
  });

  it("omits a param entirely when it is undefined or empty", async () => {
    await searchDocuments({ q: "", sort: "newest" });

    const [path] = mockedApiClient.get.mock.calls[0]!;
    const url = new URL(path as string, "https://example.com");
    expect(url.searchParams.has("q")).toBe(false);
    expect(url.searchParams.get("sort")).toBe("newest");
  });
});

describe("getDocumentStats", () => {
  it("maps the wire response (snake_case, nested documents) to the app shape", async () => {
    mockedApiClient.get.mockResolvedValue({
      total_documents: 12,
      total_storage_bytes: 4096,
      documents_by_type: { "text/plain": 10, "application/pdf": 2 },
      recent_uploads: [
        {
          id: "doc-1",
          filename: "notes.txt",
          content_type: "text/plain",
          size_bytes: 100,
          status: "ready",
          error_message: null,
          created_at: "2026-07-28T00:00:00Z",
        },
      ],
    });

    const stats = await getDocumentStats();

    expect(mockedApiClient.get).toHaveBeenCalledWith("/documents/stats", {
      signal: undefined,
    });
    expect(stats).toEqual({
      totalDocuments: 12,
      totalStorageBytes: 4096,
      documentsByType: { "text/plain": 10, "application/pdf": 2 },
      recentUploads: [
        {
          id: "doc-1",
          filename: "notes.txt",
          contentType: "text/plain",
          sizeBytes: 100,
          status: "ready",
          errorMessage: null,
          createdAt: "2026-07-28T00:00:00Z",
        },
      ],
    });
  });
});

describe("downloadDocument", () => {
  it("triggers a real browser download via a hidden anchor, not a fetch()", () => {
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const appendSpy = vi.spyOn(document.body, "appendChild");

    downloadDocument("doc-123");

    expect(appendSpy).toHaveBeenCalledTimes(1);
    const anchor = appendSpy.mock.calls[0]![0] as HTMLAnchorElement;
    expect(anchor.tagName).toBe("A");
    expect(anchor.href).toBe(
      "https://api.example.com/documents/download/doc-123"
    );
    expect(clickSpy).toHaveBeenCalledTimes(1);

    clickSpy.mockRestore();
    appendSpy.mockRestore();
  });
});

describe("toKbDocument", () => {
  const base: UploadedDocument = {
    id: "doc-1",
    filename: "report.pdf",
    contentType: "application/pdf",
    sizeBytes: 2048,
    status: "ready",
    errorMessage: null,
    createdAt: "2026-07-28T00:00:00Z",
  };

  it("maps filename, content type, and size onto the KB Document shape", () => {
    const result = toKbDocument(base, "Ava Thompson");

    expect(result.id).toBe("doc-1");
    expect(result.title).toBe("report.pdf");
    expect(result.fileType).toBe("pdf");
    expect(result.author).toBe("Ava Thompson");
    expect(result.updatedAt).toBe("2026-07-28T00:00:00Z");
  });

  it("never fabricates a folder/category/tags for a real document", () => {
    const result = toKbDocument(base, "Ava Thompson");

    expect(result.folderId).toBe("");
    expect(result.categoryId).toBe("");
    expect(result.tagIds).toEqual([]);
  });

  it.each([
    ["uploaded", "Uploaded."],
    ["processing", "Processing — extracting content…"],
    ["embedding", "Generating embeddings…"],
    ["ready", "Ready — fully indexed and searchable."],
    ["failed", "Processing failed — this file couldn't be indexed."],
  ] as const)("derives the excerpt from status %s", (status, expectedExcerpt) => {
    const result = toKbDocument({ ...base, status }, "Ava Thompson");
    expect(result.excerpt).toBe(expectedExcerpt);
  });
});
