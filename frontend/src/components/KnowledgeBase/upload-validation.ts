const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;
const MAX_FILE_SIZE_LABEL = "25 MB";

// Matches services/document_service.py's ACCEPTED_UPLOAD_CONTENT_TYPES
// exactly — verified directly against that file, not guessed. Kept as
// extensions here (not MIME types) since that's what a file input's
// `accept` attribute and a client-side filename check both work with;
// the backend is what actually validates content_type.
const ACCEPTED_EXTENSIONS = [
  ".txt",
  ".md",
  ".pdf",
  ".docx",
  ".csv",
  ".png",
  ".jpg",
  ".jpeg",
];

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
