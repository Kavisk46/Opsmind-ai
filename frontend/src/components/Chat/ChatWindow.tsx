"use client";

import { useEffect, useRef, useState } from "react";

import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import conversationData from "@/lib/mock-data/conversation.json";
import { toast } from "@/lib/toast";

import { sendChatMessage } from "./chat-api";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import { streamText } from "./stream-text";
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
  const cancelStreamRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      cancelStreamRef.current?.();
    };
  }, []);

  // Shared by both a brand-new send and a regenerate: calls the mock API for
  // a fresh reply, then streams it word-by-word into a target message.
  // `existingMessageId` distinguishes the two cases — when set (regenerate),
  // that message's content/timestamp are reset and reused as the streaming
  // target instead of appending a new message.
  const beginStreamingReply = async (
    promptContent: string,
    existingMessageId?: string
  ) => {
    if (existingMessageId) {
      setMessages((prev) =>
        prev.map((existing) =>
          existing.id === existingMessageId
            ? { ...existing, content: "", createdAt: new Date().toISOString() }
            : existing
        )
      );
      setStreamingMessageId(existingMessageId);
    } else {
      setIsLoading(true);
    }

    try {
      const { message } = await sendChatMessage(promptContent);
      const targetId = existingMessageId ?? message.id;

      if (!existingMessageId) {
        setIsLoading(false);
        setMessages((prev) => [...prev, { ...message, content: "" }]);
        setStreamingMessageId(targetId);
      }

      cancelStreamRef.current = streamText(
        message.content,
        (partial) => {
          setMessages((prev) =>
            prev.map((existing) =>
              existing.id === targetId
                ? { ...existing, content: partial }
                : existing
            )
          );
        },
        () => {
          setStreamingMessageId(null);
          cancelStreamRef.current = null;
        }
      );
    } catch (error) {
      setIsLoading(false);
      setStreamingMessageId(null);
      toast(getFriendlyErrorMessage(normalizeError(error)));
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
