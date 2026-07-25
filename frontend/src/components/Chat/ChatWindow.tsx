"use client";

import { useEffect, useRef, useState } from "react";

import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import conversationData from "@/lib/mock-data/conversation.json";
import { toast } from "@/lib/toast";

import { createConversation, streamChatMessage } from "./chat-api";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import type { Message } from "./types";

const seedMessages = conversationData as Message[];

interface ChatWindowProps {
  initialMessages?: Message[];
}

export function ChatWindow({ initialMessages = seedMessages }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null
  );
  const abortControllerRef = useRef<AbortController | null>(null);
  // The real backend conversation this window is talking to — separate
  // from AssistantConsole's mock sidebar `activeConversationId` (see
  // AssistantConsole.tsx/ConversationList.tsx, both still driven by mock
  // JSON, unchanged by this integration). Starts unset; the FIRST message
  // sent in a mounted ChatWindow creates a real conversation via
  // POST /conversations and every later message in this window (including
  // regenerate) reuses that same id, which is what gives the backend the
  // prior turns it needs to answer with conversation history.
  const conversationIdRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

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
        const conversation = await createConversation({
          signal: controller.signal,
        });
        conversationIdRef.current = conversation.id;
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
      <MessageList
        messages={messages}
        isLoading={isLoading}
        streamingMessageId={streamingMessageId}
        isBusy={isBusy}
        onRegenerate={handleRegenerate}
      />
      <ChatInput onSend={handleSend} disabled={isBusy} />
    </div>
  );
}
