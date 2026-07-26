import { Pin, Trash2 } from "lucide-react";

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
};

export function ConversationCard({
  title,
  lastMessagePreview,
  updatedAt,
  isPinned,
  isActive,
  onSelect,
  onDelete,
}: ConversationCardProps) {
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
