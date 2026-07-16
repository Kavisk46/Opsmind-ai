import type { Document, Folder, FolderNode } from "./types";

export function buildFolderTree(folders: Folder[]): FolderNode[] {
  const nodesById = new Map<string, FolderNode>(
    folders.map((folder) => [folder.id, { ...folder, children: [] }])
  );
  const roots: FolderNode[] = [];

  for (const folder of folders) {
    const node = nodesById.get(folder.id);
    if (!node) {
      continue;
    }
    const parent = folder.parentId ? nodesById.get(folder.parentId) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

// Includes the folder itself — selecting a parent folder should surface
// documents filed anywhere underneath it, not just ones filed directly on
// that exact folder (most documents live in leaf folders, so filtering
// strictly by id alone would make parent folders look empty).
export function getDescendantFolderIds(
  folders: Folder[],
  folderId: string
): string[] {
  const childrenByParent = new Map<string, string[]>();
  for (const folder of folders) {
    if (folder.parentId === null) {
      continue;
    }
    const siblings = childrenByParent.get(folder.parentId) ?? [];
    siblings.push(folder.id);
    childrenByParent.set(folder.parentId, siblings);
  }

  const result: string[] = [];
  const stack = [folderId];
  while (stack.length > 0) {
    const currentId = stack.pop();
    if (currentId === undefined) {
      continue;
    }
    result.push(currentId);
    stack.push(...(childrenByParent.get(currentId) ?? []));
  }

  return result;
}

// Root-to-leaf ancestor chain, including the folder itself — used to build
// the in-page breadcrumb trail for the selected folder.
export function getFolderPath(folders: Folder[], folderId: string): Folder[] {
  const foldersById = new Map(folders.map((folder) => [folder.id, folder]));
  const path: Folder[] = [];

  let current = foldersById.get(folderId);
  while (current) {
    path.unshift(current);
    current = current.parentId ? foldersById.get(current.parentId) : undefined;
  }

  return path;
}

export function countDocumentsInFolder(
  documents: Document[],
  folders: Folder[],
  folderId: string
): number {
  const descendantIds = new Set(getDescendantFolderIds(folders, folderId));
  return documents.filter((document) => descendantIds.has(document.folderId))
    .length;
}
