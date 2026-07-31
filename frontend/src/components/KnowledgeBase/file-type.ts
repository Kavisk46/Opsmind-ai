import {
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  Presentation,
  type LucideIcon,
} from "lucide-react";

import type { FileType } from "./types";

interface FileTypeConfig {
  icon: LucideIcon;
  label: string;
}

// Deliberately uniform, non-semantic styling (no red/green/etc.) — file type
// is a category, not a status, so it's differentiated by icon + label only.
const FILE_TYPE_CONFIG: Record<FileType, FileTypeConfig> = {
  markdown: { icon: FileCode, label: "Markdown" },
  pdf: { icon: FileText, label: "PDF" },
  doc: { icon: FileText, label: "Word Doc" },
  sheet: { icon: FileSpreadsheet, label: "Spreadsheet" },
  slide: { icon: Presentation, label: "Slides" },
  image: { icon: FileImage, label: "Image" },
  text: { icon: FileText, label: "Text" },
  csv: { icon: FileSpreadsheet, label: "CSV" },
};

export function getFileTypeConfig(fileType: FileType): FileTypeConfig {
  return FILE_TYPE_CONFIG[fileType];
}

// Maps the backend's real MIME type (schemas/document.py's content_type
// field) onto this module's existing FileType categories — the one place
// that mapping lives, so DocumentCard/DocumentViewer/DocumentMeta never
// need to know about raw MIME strings themselves.
const CONTENT_TYPE_TO_FILE_TYPE: Record<string, FileType> = {
  "text/plain": "text",
  "text/markdown": "markdown",
  "application/pdf": "pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "doc",
  "text/csv": "csv",
  "image/png": "image",
  "image/jpeg": "image",
};

export function contentTypeToFileType(contentType: string): FileType {
  return CONTENT_TYPE_TO_FILE_TYPE[contentType] ?? "text";
}
