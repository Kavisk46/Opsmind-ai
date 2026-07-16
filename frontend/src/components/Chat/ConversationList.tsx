"use client";

import { Plus, Search, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import { ConversationCard } from "./ConversationCard";
import type { Conversation } from "./types";

interface ConversationListProps {
  conversations: Conversation[];
  activeConversationId: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  // Provided only by the mobile modal instance — its presence is what
  // turns on the close button, Escape-to-close, and body-scroll lock.
  onClose?: () => void;
}

export function ConversationList({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onClose,
}: ConversationListProps) {
  const [query, setQuery] = useState("");
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useModalDismiss({ onClose, closeButtonRef, containerRef });

  const visibleConversations = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const matches = normalized
      ? conversations.filter(
          (conversation) =>
            conversation.title.toLowerCase().includes(normalized) ||
            conversation.lastMessagePreview.toLowerCase().includes(normalized)
        )
      : conversations;

    return [...matches].sort((a, b) => Number(b.isPinned) - Number(a.isPinned));
  }, [query, conversations]);

  return (
    <div
      ref={containerRef}
      className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-border bg-card lg:h-[calc(100vh-14rem)] lg:w-72 lg:shrink-0"
    >
      <div className="flex items-center gap-2 border-b border-border p-3">
        <Button
          type="button"
          onClick={onNewChat}
          className="flex-1 justify-center gap-2"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          New Chat
        </Button>
        {onClose && (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close conversations"
            className={cn(
              "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
              FOCUS_RING_CLASS
            )}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="p-3">
        <label htmlFor="conversation-search" className="sr-only">
          Search conversations
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            id="conversation-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search conversations…"
            className={cn(
              "w-full rounded-md border border-border bg-background py-2 pr-3 pl-8 text-sm text-foreground placeholder:text-muted-foreground",
              FOCUS_RING_CLASS
            )}
          />
        </div>
      </div>

      <nav
        aria-label="Conversations"
        className="flex-1 space-y-1 overflow-y-auto px-2 pb-2"
      >
        {visibleConversations.length === 0 ? (
          <p className="px-3 py-4 text-center text-sm text-muted-foreground">
            No conversations found.
          </p>
        ) : (
          visibleConversations.map((conversation) => (
            <ConversationCard
              key={conversation.id}
              title={conversation.title}
              lastMessagePreview={conversation.lastMessagePreview}
              updatedAt={conversation.updatedAt}
              isPinned={conversation.isPinned}
              isActive={conversation.id === activeConversationId}
              onSelect={() => onSelectConversation(conversation.id)}
            />
          ))
        )}
      </nav>
    </div>
  );
}
