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
};

export function getFileTypeConfig(fileType: FileType): FileTypeConfig {
  return FILE_TYPE_CONFIG[fileType];
}
