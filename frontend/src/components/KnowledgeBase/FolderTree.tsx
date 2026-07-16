"use client";

import { ChevronDown, ChevronRight, Folder as FolderIcon, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { cn } from "@/lib/utils";

import { buildFolderTree, countDocumentsInFolder } from "./folder-tree";
import type { Document, Folder, FolderNode } from "./types";

interface FolderTreeProps {
  folders: Folder[];
  documents: Document[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  // Provided only by the mobile modal instance — matches ConversationList's
  // established onClose pattern (close button, Escape, body-scroll lock).
  onClose?: () => void;
}

export function FolderTree({
  folders,
  documents,
  selectedFolderId,
  onSelectFolder,
  onClose,
}: FolderTreeProps) {
  const tree = useMemo(() => buildFolderTree(folders), [folders]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () =>
      new Set(
        folders
          .filter((folder) => folders.some((f) => f.parentId === folder.id))
          .map((folder) => folder.id)
      )
  );
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useModalDismiss({ onClose, closeButtonRef, containerRef });

  const toggleExpanded = (folderId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  };

  const renderNode = (node: FolderNode, depth: number) => {
    const isExpanded = expandedIds.has(node.id);
    const isActive = node.id === selectedFolderId;
    const count = countDocumentsInFolder(documents, folders, node.id);

    return (
      <li key={node.id}>
        <div
          className={cn(
            "flex items-center gap-1 rounded-md pr-2",
            isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
          )}
          style={{ paddingLeft: `${depth * 1}rem` }}
        >
          {node.children.length > 0 ? (
            <button
              type="button"
              onClick={() => toggleExpanded(node.id)}
              aria-label={isExpanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
              aria-expanded={isExpanded}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </button>
          ) : (
            <span className="h-7 w-7 shrink-0" aria-hidden="true" />
          )}
          <button
            type="button"
            onClick={() => onSelectFolder(node.id)}
            aria-current={isActive ? "true" : undefined}
            className="flex min-w-0 flex-1 items-center gap-2 truncate rounded-md py-1.5 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <FolderIcon
              className="h-4 w-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <span className="truncate">{node.name}</span>
            <span className="ml-auto shrink-0 text-xs text-muted-foreground">
              {count}
            </span>
          </button>
        </div>
        {node.children.length > 0 && isExpanded && (
          <ul>{node.children.map((child) => renderNode(child, depth + 1))}</ul>
        )}
      </li>
    );
  };

  return (
    <div
      ref={containerRef}
      className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-border bg-card lg:h-[calc(100vh-14rem)] lg:w-64 lg:shrink-0"
    >
      <div className="flex items-center justify-between gap-2 border-b border-border p-3">
        <h2 className="text-sm font-semibold text-foreground">Folders</h2>
        {onClose && (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close folders"
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      <nav aria-label="Folders" className="flex-1 space-y-0.5 overflow-y-auto p-2">
        <button
          type="button"
          onClick={() => onSelectFolder(null)}
          aria-current={selectedFolderId === null ? "true" : undefined}
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            selectedFolderId === null
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50"
          )}
        >
          <FolderIcon
            className="h-4 w-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <span>All Documents</span>
          <span className="ml-auto text-xs text-muted-foreground">
            {documents.length}
          </span>
        </button>
        <ul className="mt-1 space-y-0.5">
          {tree.map((node) => renderNode(node, 0))}
        </ul>
      </nav>
    </div>
  );
}
