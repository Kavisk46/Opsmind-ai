import { Pencil, Pin, Trash2 } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

import { formatRelativeTime } from "@/components/ActivityList";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import type { Conversation } from "./types";

type ConversationCardProps = Pick<
  Conversation,
  "title" | "lastMessagePreview" | "updatedAt" | "isPinned"
> & {
  isActive: boolean;
  onSelect: () => void;
  onDelete?: () => void;
  onRename?: (newTitle: string) => void;
};

export function ConversationCard({
  title,
  lastMessagePreview,
  updatedAt,
  isPinned,
  isActive,
  onSelect,
  onDelete,
  onRename,
}: ConversationCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(title);

  const startEditing = () => {
    setDraftTitle(title);
    setIsEditing(true);
  };

  const commitEdit = () => {
    const trimmed = draftTitle.trim();
    setIsEditing(false);
    // Same "empty/unchanged is a no-op, not an error" reasoning as most
    // inline-rename UIs — only a real, different title is worth a
    // network call.
    if (trimmed && trimmed !== title) {
      onRename?.(trimmed);
    }
  };

  const handleEditKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitEdit();
    } else if (event.key === "Escape") {
      event.preventDefault();
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 rounded-md px-3 py-2.5">
        <label htmlFor="conversation-rename-input" className="sr-only">
          Rename conversation
        </label>
        <input
          id="conversation-rename-input"
          type="text"
          value={draftTitle}
          onChange={(event) => setDraftTitle(event.target.value)}
          onKeyDown={handleEditKeyDown}
          onBlur={commitEdit}
          autoFocus
          maxLength={200}
          className={cn(
            "min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground",
            FOCUS_RING_CLASS
          )}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-1 rounded-md transition-colors",
        isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-current={isActive ? "true" : undefined}
        className={cn(
          "flex min-w-0 flex-1 flex-col gap-1 rounded-md px-3 py-2.5 text-left",
          FOCUS_RING_CLASS
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {title}
          </span>
          {isPinned && (
            <Pin
              className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          )}
        </div>
        {lastMessagePreview && (
          <p className="truncate text-xs text-muted-foreground">
            {lastMessagePreview}
          </p>
        )}
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(updatedAt)}
        </span>
      </button>
      {onRename && (
        <button
          type="button"
          onClick={startEditing}
          aria-label={`Rename ${title}`}
          className={cn(
            "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-foreground group-hover:opacity-100 group-focus-within:opacity-100",
            FOCUS_RING_CLASS
          )}
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
      {onDelete && (
        <button
          type="button"
          onClick={onDelete}
          aria-label={`Delete ${title}`}
          className={cn(
            "mr-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-destructive group-hover:opacity-100 group-focus-within:opacity-100",
            FOCUS_RING_CLASS
          )}
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
