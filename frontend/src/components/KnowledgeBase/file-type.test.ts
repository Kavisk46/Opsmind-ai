import { describe, expect, it } from "vitest";

import { contentTypeToFileType, getFileTypeConfig } from "./file-type";

describe("contentTypeToFileType", () => {
  it.each([
    ["text/plain", "text"],
    ["text/markdown", "markdown"],
    ["application/pdf", "pdf"],
    [
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "doc",
    ],
    ["text/csv", "csv"],
    ["image/png", "image"],
    ["image/jpeg", "image"],
  ] as const)("maps %s to %s", (contentType, expected) => {
    expect(contentTypeToFileType(contentType)).toBe(expected);
  });

  it("falls back to text for an unrecognized content type", () => {
    expect(contentTypeToFileType("application/zip")).toBe("text");
  });
});

describe("getFileTypeConfig", () => {
  it("returns a config for every FileType this module maps to", () => {
    for (const fileType of [
      "markdown",
      "pdf",
      "doc",
      "sheet",
      "slide",
      "image",
      "text",
      "csv",
    ] as const) {
      const config = getFileTypeConfig(fileType);
      expect(config.label).toBeTruthy();
      expect(config.icon).toBeDefined();
    }
  });
});
