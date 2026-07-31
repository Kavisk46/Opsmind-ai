import { describe, expect, it } from "vitest";

import { filterDocuments, sortDocuments } from "./document-filters";
import type { Document } from "./types";

function makeDocument(overrides: Partial<Document> & { id: string }): Document {
  return {
    title: "Untitled",
    folderId: "",
    fileType: "text",
    categoryId: "",
    tagIds: [],
    author: "You",
    updatedAt: "2026-01-01T00:00:00.000Z",
    sizeLabel: "1 KB",
    excerpt: "Ready.",
    ...overrides,
  };
}

const baseOptions = {
  query: "",
  categoryId: null,
  tagIds: [] as string[],
  folderDescendantIds: null,
  viewMode: "all" as const,
  favoriteIds: [] as string[],
  recentIds: [] as string[],
};

describe("filterDocuments", () => {
  const documents = [
    makeDocument({ id: "1", title: "Quarterly Report" }),
    makeDocument({ id: "2", title: "Meeting Notes" }),
  ];

  it("returns everything when no filters are active", () => {
    expect(filterDocuments(documents, baseOptions)).toHaveLength(2);
  });

  it("matches query against the title", () => {
    const result = filterDocuments(documents, { ...baseOptions, query: "report" });
    expect(result.map((d) => d.id)).toEqual(["1"]);
  });

  it("matches query case-insensitively against the excerpt", () => {
    const withExcerpt = [
      makeDocument({ id: "1", title: "A", excerpt: "Contains BUDGET figures" }),
      makeDocument({ id: "2", title: "B", excerpt: "Unrelated content" }),
    ];
    const result = filterDocuments(withExcerpt, { ...baseOptions, query: "budget" });
    expect(result.map((d) => d.id)).toEqual(["1"]);
  });

  it("filters to only favorited documents in the favorites view", () => {
    const result = filterDocuments(documents, {
      ...baseOptions,
      viewMode: "favorites",
      favoriteIds: ["2"],
    });
    expect(result.map((d) => d.id)).toEqual(["2"]);
  });

  it("orders the recent view by most-recently-viewed first", () => {
    const result = filterDocuments(documents, {
      ...baseOptions,
      viewMode: "recent",
      recentIds: ["2", "1"],
    });
    expect(result.map((d) => d.id)).toEqual(["2", "1"]);
  });

  it("filters by folder descendant ids", () => {
    const withFolders = [
      makeDocument({ id: "1", folderId: "folder-a" }),
      makeDocument({ id: "2", folderId: "folder-b" }),
    ];
    const result = filterDocuments(withFolders, {
      ...baseOptions,
      folderDescendantIds: ["folder-a"],
    });
    expect(result.map((d) => d.id)).toEqual(["1"]);
  });

  it("filters by category", () => {
    const withCategories = [
      makeDocument({ id: "1", categoryId: "cat-a" }),
      makeDocument({ id: "2", categoryId: "cat-b" }),
    ];
    const result = filterDocuments(withCategories, {
      ...baseOptions,
      categoryId: "cat-a",
    });
    expect(result.map((d) => d.id)).toEqual(["1"]);
  });

  it("filters by any matching tag", () => {
    const withTags = [
      makeDocument({ id: "1", tagIds: ["urgent"] }),
      makeDocument({ id: "2", tagIds: ["archived"] }),
    ];
    const result = filterDocuments(withTags, {
      ...baseOptions,
      tagIds: ["urgent"],
    });
    expect(result.map((d) => d.id)).toEqual(["1"]);
  });

  it("returns nothing for a real backend document with no folders/categories/tags configured", () => {
    // Every real document adapted via documents-api.ts's toKbDocument has
    // folderId/categoryId/tagIds all empty/blank — this proves that
    // selecting a specific folder/category/tag correctly excludes real
    // documents rather than matching them by accident on an empty string.
    const realStyleDocuments = [makeDocument({ id: "1" })];
    expect(
      filterDocuments(realStyleDocuments, {
        ...baseOptions,
        folderDescendantIds: ["some-folder"],
      })
    ).toHaveLength(0);
  });
});

describe("sortDocuments", () => {
  const documents = [
    makeDocument({ id: "1", title: "Banana", updatedAt: "2026-01-02T00:00:00.000Z" }),
    makeDocument({ id: "2", title: "Apple", updatedAt: "2026-01-03T00:00:00.000Z" }),
    makeDocument({ id: "3", title: "Cherry", updatedAt: "2026-01-01T00:00:00.000Z" }),
  ];

  it("sorts updated-desc newest first", () => {
    expect(sortDocuments(documents, "updated-desc").map((d) => d.id)).toEqual([
      "2",
      "1",
      "3",
    ]);
  });

  it("sorts updated-asc oldest first", () => {
    expect(sortDocuments(documents, "updated-asc").map((d) => d.id)).toEqual([
      "3",
      "1",
      "2",
    ]);
  });

  it("sorts title-asc alphabetically", () => {
    expect(sortDocuments(documents, "title-asc").map((d) => d.id)).toEqual([
      "2",
      "1",
      "3",
    ]);
  });

  it("sorts title-desc reverse-alphabetically", () => {
    expect(sortDocuments(documents, "title-desc").map((d) => d.id)).toEqual([
      "3",
      "1",
      "2",
    ]);
  });

  it("does not mutate the original array", () => {
    const original = [...documents];
    sortDocuments(documents, "title-asc");
    expect(documents).toEqual(original);
  });
});
