import { Pin } from "lucide-react";

import { formatRelativeTime } from "@/components/ActivityList";
import { cn } from "@/lib/utils";

import type { Conversation } from "./types";

type ConversationCardProps = Pick<
  Conversation,
  "title" | "lastMessagePreview" | "updatedAt" | "isPinned"
> & {
  isActive: boolean;
  onSelect: () => void;
};

export function ConversationCard({
  title,
  lastMessagePreview,
  updatedAt,
  isPinned,
  isActive,
  onSelect,
}: ConversationCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={isActive ? "true" : undefined}
      className={cn(
        "flex w-full flex-col gap-1 rounded-md px-3 py-2.5 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
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
      <p className="truncate text-xs text-muted-foreground">
        {lastMessagePreview}
      </p>
      <span className="text-xs text-muted-foreground">
        {formatRelativeTime(updatedAt)}
      </span>
    </button>
  );
}
