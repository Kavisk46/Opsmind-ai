// "text" and "csv" cover the real backend's text/plain and text/csv
// uploads — added here rather than folded into an existing bucket since
// neither is genuinely a markdown/doc/sheet/slide/image.
export type FileType =
  | "markdown"
  | "pdf"
  | "doc"
  | "sheet"
  | "slide"
  | "image"
  | "text"
  | "csv";

export interface Folder {
  id: string;
  name: string;
  parentId: string | null;
}

export interface FolderNode extends Folder {
  children: FolderNode[];
}

export interface Category {
  id: string;
  name: string;
}

export interface Tag {
  id: string;
  name: string;
}

export interface Document {
  id: string;
  title: string;
  folderId: string;
  fileType: FileType;
  categoryId: string;
  tagIds: string[];
  author: string;
  updatedAt: string;
  sizeLabel: string;
  excerpt: string;
  // Only meaningful for fileType "markdown" — other file types have no
  // renderable body in this mock (no backend to convert/extract one).
  content?: string;
  // Only meaningful for fileType "image".
  previewImageUrl?: string;
}

export type SortOption = "updated-desc" | "updated-asc" | "title-asc" | "title-desc";

export type ViewMode = "all" | "favorites" | "recent";
