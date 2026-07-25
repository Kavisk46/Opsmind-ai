const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
const MAX_FILE_SIZE_LABEL = "20 MB";

// Matches backend/core/text_extraction.py's SUPPORTED_CONTENT_TYPES
// exactly (text/plain, text/markdown, application/pdf) — verified
// directly against that file, not guessed. A much broader mock list
// (.doc, .xls, .png, ...) used to live here; uploading any of those would
// pass this check but then fail on the backend with a 415, so this list
// is corrected to match what the real upload endpoint actually accepts.
const ACCEPTED_EXTENSIONS = [".txt", ".md", ".pdf"];

export const UPLOAD_ACCEPT_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(",");

function getExtension(filename: string): string {
  const match = /\.[^.]+$/.exec(filename);
  return match ? match[0].toLowerCase() : "";
}

// Client-side pre-check so an obviously-wrong file never reaches the
// network — the backend re-validates all of this independently
// (api/routes/documents.py / services/document_service.py) and remains
// the actual source of truth; this only saves a round trip for the
// common case.
export function validateFile(file: File): string | null {
  const extension = getExtension(file.name);

  if (!ACCEPTED_EXTENSIONS.includes(extension)) {
    return `${extension || "This file type"} isn't supported. Accepted types: ${ACCEPTED_EXTENSIONS.join(", ")}.`;
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large — the limit is ${MAX_FILE_SIZE_LABEL}.`;
  }

  return null;
}
