import { describe, expect, it } from "vitest";

import { validateFile } from "./upload-validation";

function makeFile(name: string, sizeBytes: number, type = "text/plain"): File {
  return new File([new Uint8Array(sizeBytes)], name, { type });
}

describe("validateFile", () => {
  it("accepts every extension the backend accepts", () => {
    for (const name of [
      "notes.txt",
      "README.md",
      "report.pdf",
      "contract.docx",
      "data.csv",
      "diagram.png",
      "photo.jpg",
      "photo.jpeg",
    ]) {
      expect(validateFile(makeFile(name, 1024))).toBeNull();
    }
  });

  it("rejects an unsupported extension", () => {
    const error = validateFile(makeFile("archive.zip", 1024));
    expect(error).toContain(".zip");
  });

  it("rejects a file over the 25 MB limit", () => {
    const oversized = makeFile("big.txt", 25 * 1024 * 1024 + 1);
    const error = validateFile(oversized);
    expect(error).toContain("25 MB");
  });

  it("accepts a file exactly at the 25 MB limit", () => {
    const atLimit = makeFile("exact.txt", 25 * 1024 * 1024);
    expect(validateFile(atLimit)).toBeNull();
  });
});
