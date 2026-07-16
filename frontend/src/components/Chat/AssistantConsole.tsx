"use client";

import { MessageSquare } from "lucide-react";
import { useState } from "react";

import conversationsData from "@/lib/mock-data/conversations.json";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import { ChatWindow } from "./ChatWindow";
import { ConversationList } from "./ConversationList";
import type { Conversation } from "./types";

const seedConversations = conversationsData as Conversation[];
const DEFAULT_CONVERSATION_ID = seedConversations[0]?.id ?? "";

function createEmptyConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    updatedAt: new Date().toISOString(),
    lastMessagePreview: "No messages yet",
    isPinned: false,
    messageCount: 0,
  };
}

export function AssistantConsole() {
  const [conversations, setConversations] =
    useState<Conversation[]>(seedConversations);
  const [activeConversationId, setActiveConversationId] = useState(
    DEFAULT_CONVERSATION_ID
  );
  const [isListOpen, setIsListOpen] = useState(false);

  const handleNewChat = () => {
    const conversation = createEmptyConversation();
    setConversations((prev) => [conversation, ...prev]);
    setActiveConversationId(conversation.id);
    setIsListOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    setIsListOpen(false);
  };

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId
  );

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <button
        type="button"
        onClick={() => setIsListOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={isListOpen}
        className={cn(
          "flex items-center gap-2 rounded-lg border border-border bg-card p-3 text-left lg:hidden",
          FOCUS_RING_CLASS
        )}
      >
        <MessageSquare
          className="h-4 w-4 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <span className="truncate text-sm font-medium text-foreground">
          {activeConversation?.title ?? "Conversations"}
        </span>
      </button>

      <div className="hidden lg:block">
        <ConversationList
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={setActiveConversationId}
          onNewChat={handleNewChat}
        />
      </div>

      {isListOpen && (
        <div
          className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80 lg:hidden"
          onClick={() => setIsListOpen(false)}
          aria-hidden="true"
        />
      )}
      {isListOpen && (
        <div className="fixed inset-x-4 top-20 bottom-4 z-(--z-modal) animate-scale-in motion-reduce:animate-none lg:hidden">
          <ConversationList
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={handleSelectConversation}
            onNewChat={handleNewChat}
            onClose={() => setIsListOpen(false)}
          />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <ChatWindow
          key={activeConversationId}
          initialMessages={
            activeConversationId === DEFAULT_CONVERSATION_ID ? undefined : []
          }
        />
      </div>
    </div>
  );
}
