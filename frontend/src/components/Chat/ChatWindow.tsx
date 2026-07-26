"use client";

import { useEffect, useRef, useState } from "react";

import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { toast } from "@/lib/toast";

import { createConversation, streamChatMessage, useConversation } from "./chat-api";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import type { Message } from "./types";

interface ChatWindowProps {
  // null means "no conversation selected yet" — a brand-new, not-yet-
  // created chat. A real id means AssistantConsole selected an existing
  // conversation and its history should be loaded from the backend.
  conversationId: string | null;
  // Fired the moment this window creates a NEW conversation (on the first
  // message of a fresh chat) — lets AssistantConsole add the real
  // conversation to its sidebar immediately, with its real backend-
  // assigned title, instead of requiring a manual refresh.
  onConversationCreated: (conversation: { id: string; title: string }) => void;
}

export function ChatWindow({
  conversationId,
  onConversationCreated,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  // Frozen at mount, deliberately NOT the live `conversationId` prop:
  // AssistantConsole updates that prop (via onConversationCreated, below)
  // the moment THIS window creates a brand-new conversation mid-session,
  // without remounting this component — reacting to that change here
  // would fire a real GET /conversations/{id} for the conversation this
  // window just created, racing its own in-progress stream, and then
  // overwrite `messages` with whatever the backend has persisted so far
  // (possibly incomplete). useState's initializer runs once, on mount,
  // exactly like conversationIdRef below — this is the same pattern
  // applied to the history query instead of the streaming target.
  const [initialConversationId] = useState(conversationId);
  // Cached (see chat-api.ts's useConversation) — re-selecting a
  // conversation already opened earlier this session loads instantly
  // from cache instead of re-fetching and re-flashing the loading state.
  const conversationQuery = useConversation(initialConversationId);
  const isLoadingHistory =
    initialConversationId !== null && conversationQuery.isPending;
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null
  );
  const abortControllerRef = useRef<AbortController | null>(null);
  // The real backend conversation this window is talking to. Starts at
  // whatever AssistantConsole selected (possibly null, for a brand-new
  // chat); the first message sent in a null-started window creates a
  // real conversation via POST /conversations, and every later message
  // (including regenerate) reuses that same id — this is what gives the
  // backend the prior turns it needs to answer with conversation history.
  const conversationIdRef = useRef<string | null>(conversationId);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Seeds real history once it arrives, into INDEPENDENTLY mutable state
  // (not simple prop-derived state — beginStreamingReply below appends
  // streamed deltas to `messages` character by character, which is why
  // this can't just read conversationQuery.data directly during render).
  // AssistantConsole remounts this component (via `key`) whenever the
  // selected conversation changes, so `conversationQuery.data`'s
  // reference only ever changes once per mount here — safe to sync
  // without it later clobbering messages that are actively streaming in.
  useEffect(() => {
    if (conversationQuery.data) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMessages(conversationQuery.data.messages);
    }
  }, [conversationQuery.data]);

  useEffect(() => {
    if (conversationQuery.error) {
      toast(getFriendlyErrorMessage(normalizeError(conversationQuery.error)));
    }
  }, [conversationQuery.error]);

  // Shared by both a brand-new send and a regenerate: ensures a real
  // backend conversation exists, then streams a fresh reply into it via
  // POST /chat/stream. `existingMessageId` distinguishes the two cases —
  // when set (regenerate), that message's content/citations are reset and
  // reused as the streaming target instead of appending a new message.
  const beginStreamingReply = async (
    promptContent: string,
    existingMessageId?: string
  ) => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const targetId = existingMessageId ?? crypto.randomUUID();

    if (existingMessageId) {
      setMessages((prev) =>
        prev.map((existing) =>
          existing.id === existingMessageId
            ? {
                ...existing,
                content: "",
                citations: undefined,
                createdAt: new Date().toISOString(),
              }
            : existing
        )
      );
    } else {
      setIsLoading(true);
    }

    try {
      if (!conversationIdRef.current) {
        // First message of a brand-new chat — title it from the question
        // itself (see chat-api.ts's createConversation() doc comment for
        // why this app has to do that itself rather than relying on the
        // backend's own auto-titling).
        const conversation = await createConversation({
          title: promptContent,
          signal: controller.signal,
        });
        conversationIdRef.current = conversation.id;
        onConversationCreated(conversation);
      }

      if (!existingMessageId) {
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            id: targetId,
            role: "assistant",
            content: "",
            createdAt: new Date().toISOString(),
          },
        ]);
      }
      setStreamingMessageId(targetId);

      await streamChatMessage(
        { question: promptContent, conversationId: conversationIdRef.current },
        {
          onDelta: (delta) => {
            setMessages((prev) =>
              prev.map((existing) =>
                existing.id === targetId
                  ? { ...existing, content: existing.content + delta }
                  : existing
              )
            );
          },
          onDone: ({ citations }) => {
            setMessages((prev) =>
              prev.map((existing) =>
                existing.id === targetId ? { ...existing, citations } : existing
              )
            );
          },
        },
        controller.signal
      );
    } catch (error) {
      const apiError = normalizeError(error);
      // An aborted request means the window unmounted or a new send
      // superseded this one — not a real failure, so no error toast.
      if (apiError.code !== "ABORTED") {
        toast(getFriendlyErrorMessage(apiError));
      }
    } finally {
      setIsLoading(false);
      setStreamingMessageId(null);
      abortControllerRef.current = null;
    }
  };

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    await beginStreamingReply(content);
  };

  const handleRegenerate = (messageId: string) => {
    if (isBusy) {
      return;
    }

    const index = messages.findIndex((m) => m.id === messageId);
    if (index === -1) {
      return;
    }

    let promptContent: string | undefined;
    for (let i = index - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "user") {
        promptContent = messages[i]?.content;
        break;
      }
    }

    if (!promptContent) {
      return;
    }

    void beginStreamingReply(promptContent, messageId);
  };

  const isBusy = isLoading || streamingMessageId !== null;

  return (
    <div className="flex h-[calc(100vh-18rem)] min-h-[400px] flex-col overflow-hidden rounded-lg border border-border bg-card lg:h-[calc(100vh-14rem)]">
      {isLoadingHistory ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            Loading conversation…
          </p>
        </div>
      ) : (
        <MessageList
          messages={messages}
          isLoading={isLoading}
          streamingMessageId={streamingMessageId}
          isBusy={isBusy}
          onRegenerate={handleRegenerate}
        />
      )}
      <ChatInput onSend={handleSend} disabled={isBusy || isLoadingHistory} />
    </div>
  );
}
