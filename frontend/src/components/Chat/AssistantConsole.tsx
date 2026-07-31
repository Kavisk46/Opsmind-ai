"use client";

import { useQueryClient } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import {
  CONVERSATIONS_QUERY_KEY,
  deleteConversation,
  renameConversation,
  useConversations,
  type Conversation as BackendConversation,
} from "./chat-api";
import { ChatWindow } from "./ChatWindow";
import { ConversationList } from "./ConversationList";
import type { Conversation } from "./types";

// Maps the real backend shape (id/title/createdAt/updatedAt) onto the
// UI-facing Conversation type ConversationList/ConversationCard already
// render against. isPinned/messageCount have no backend equivalent —
// always false/0; lastMessagePreview is intentionally empty (see
// handleConversationCreated's comment below) rather than fabricated.
function toUiConversation(conversation: BackendConversation): Conversation {
  return {
    id: conversation.id,
    title: conversation.title,
    updatedAt: conversation.updatedAt,
    lastMessagePreview: "",
    isPinned: false,
    messageCount: 0,
  };
}

export function AssistantConsole() {
  // The query cache (see chat-api.ts) IS the source of truth for the
  // sidebar — create/delete below update it directly via
  // queryClient.setQueryData rather than keeping a second, parallel
  // local list that could drift out of sync with it.
  const conversationsQuery = useConversations();
  const queryClient = useQueryClient();
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  // Bumped only on an explicit user action (New Chat / selecting a
  // different conversation) to force ChatWindow to remount and load that
  // conversation's real history. Deliberately NOT bumped when a brand-new
  // conversation is created mid-session (see handleConversationCreated) —
  // that would throw away the messages already in memory just to
  // re-fetch the same thing from the backend.
  const [chatWindowKey, setChatWindowKey] = useState(0);
  const [isListOpen, setIsListOpen] = useState(false);
  // Guards the auto-select-most-recent-conversation effect below so it
  // only ever fires once, the first time real data arrives — not on
  // every later background refetch, which would otherwise yank the user
  // back to conversation[0] out from under whatever they're doing.
  const hasAutoSelectedRef = useRef(false);

  useEffect(() => {
    if (conversationsQuery.data && !hasAutoSelectedRef.current) {
      hasAutoSelectedRef.current = true;
      // Most-recently-active conversation first (see chat-api.ts /
      // backend ordering) — opening into it matches this console's
      // previous (mock) default of showing the top conversation.
      setActiveConversationId(conversationsQuery.data[0]?.id ?? null);
    }
  }, [conversationsQuery.data]);

  useEffect(() => {
    if (conversationsQuery.error) {
      toast(getFriendlyErrorMessage(normalizeError(conversationsQuery.error)));
    }
  }, [conversationsQuery.error]);

  const handleNewChat = () => {
    setActiveConversationId(null);
    setChatWindowKey((key) => key + 1);
    setIsListOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    setChatWindowKey((key) => key + 1);
    setIsListOpen(false);
  };

  const handleConversationCreated = (conversation: {
    id: string;
    title: string;
  }) => {
    const now = new Date().toISOString();
    queryClient.setQueryData(
      CONVERSATIONS_QUERY_KEY,
      (prev: BackendConversation[] | undefined) => [
        { id: conversation.id, title: conversation.title, createdAt: now, updatedAt: now },
        ...(prev ?? []),
      ]
    );
    // Updates the sidebar highlight only — deliberately does NOT bump
    // chatWindowKey, so the ChatWindow that just created this
    // conversation keeps running, not remounting to re-fetch history it
    // already has in memory.
    setActiveConversationId(conversation.id);
  };

  const handleDeleteConversation = (id: string) => {
    const previous = conversationsQuery.data;
    queryClient.setQueryData(
      CONVERSATIONS_QUERY_KEY,
      (prev: BackendConversation[] | undefined) =>
        (prev ?? []).filter((conversation) => conversation.id !== id)
    );

    if (activeConversationId === id) {
      setActiveConversationId(null);
      setChatWindowKey((key) => key + 1);
    }

    deleteConversation(id).catch((error) => {
      toast(getFriendlyErrorMessage(normalizeError(error)));
      // Failed server-side — restore rather than leave the sidebar
      // claiming it's gone when it isn't.
      queryClient.setQueryData(CONVERSATIONS_QUERY_KEY, previous);
    });
  };

  const handleRenameConversation = (id: string, title: string) => {
    const previous = conversationsQuery.data;
    queryClient.setQueryData(
      CONVERSATIONS_QUERY_KEY,
      (prev: BackendConversation[] | undefined) =>
        (prev ?? []).map((conversation) =>
          conversation.id === id ? { ...conversation, title } : conversation
        )
    );

    renameConversation(id, title).catch((error) => {
      toast(getFriendlyErrorMessage(normalizeError(error)));
      // Failed server-side (e.g. the 400 an empty title would trigger) —
      // restore rather than leave the sidebar showing a title the
      // backend never actually accepted.
      queryClient.setQueryData(CONVERSATIONS_QUERY_KEY, previous);
    });
  };

  const conversations = (conversationsQuery.data ?? []).map(toUiConversation);
  const isLoadingConversations = conversationsQuery.isPending;
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
        {isLoadingConversations ? (
          <div className="flex h-full w-72 shrink-0 items-center justify-center rounded-lg border border-border bg-card p-4 lg:h-[calc(100vh-14rem)]">
            <p className="text-sm text-muted-foreground">Loading…</p>
          </div>
        ) : (
          <ConversationList
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={handleSelectConversation}
            onNewChat={handleNewChat}
            onDeleteConversation={handleDeleteConversation}
            onRenameConversation={handleRenameConversation}
          />
        )}
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
            onDeleteConversation={handleDeleteConversation}
            onRenameConversation={handleRenameConversation}
            onClose={() => setIsListOpen(false)}
          />
        </div>
      )}

      <div className="min-w-0 flex-1">
        {isLoadingConversations ? (
          <div className="flex h-[calc(100vh-18rem)] min-h-[400px] items-center justify-center rounded-lg border border-border bg-card lg:h-[calc(100vh-14rem)]">
            <p className="text-sm text-muted-foreground">Loading…</p>
          </div>
        ) : (
          // Only ever first-rendered once the initial conversations query
          // has resolved — so its very first mount already has the
          // correct starting conversationId, rather than always starting
          // null and silently missing the auto-selected conversation's
          // history (chatWindowKey only changes on a LATER explicit
          // selection, not on this initial load).
          <ChatWindow
            key={chatWindowKey}
            conversationId={activeConversationId}
            onConversationCreated={handleConversationCreated}
          />
        )}
      </div>
    </div>
  );
}
