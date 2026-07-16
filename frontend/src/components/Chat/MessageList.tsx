"use client";

import { ArrowDown, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { MessageBubble } from "./MessageBubble";
import type { Message } from "./types";
import { TypingIndicator } from "./TypingIndicator";

const NEAR_BOTTOM_THRESHOLD_PX = 80;

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  streamingMessageId: string | null;
  isBusy: boolean;
  onRegenerate: (messageId: string) => void;
}

function isGroupStart(messages: Message[], index: number) {
  const previous = messages[index - 1];
  return previous === undefined || previous.role !== messages[index]?.role;
}

function isGroupEnd(messages: Message[], index: number) {
  const next = messages[index + 1];
  return next === undefined || next.role !== messages[index]?.role;
}

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function MessageList({
  messages,
  isLoading,
  streamingMessageId,
  isBusy,
  onRegenerate,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const isFirstRenderRef = useRef(true);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  // Tracks whether the user is parked near the bottom, independent of the
  // render cycle — read from inside the effect below without needing it as
  // a dependency (a state variable here would risk a stale read).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    function handleScroll() {
      if (!container) {
        return;
      }
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      const nearBottom = distanceFromBottom < NEAR_BOTTOM_THRESHOLD_PX;
      isNearBottomRef.current = nearBottom;
      setShowJumpToBottom(!nearBottom);
    }

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    // First paint (including remounting into a different conversation via
    // `key`) restores position instantly — an animated catch-up scroll here
    // would look like the page hasn't finished loading yet. Later updates
    // only follow along if the user hasn't scrolled away to read history.
    if (isFirstRenderRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "auto" });
      isFirstRenderRef.current = false;
      return;
    }

    if (isNearBottomRef.current) {
      bottomRef.current?.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
      });
    } else {
      setShowJumpToBottom(true);
    }
  }, [messages, isLoading]);

  const jumpToBottom = () => {
    bottomRef.current?.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
    setShowJumpToBottom(false);
  };

  return (
    <div className="relative flex-1 overflow-hidden">
      <div
        ref={containerRef}
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        tabIndex={0}
        className="h-full overflow-y-auto p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        {messages.length === 0 && !isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Sparkles
              className="h-8 w-8 text-muted-foreground"
              aria-hidden="true"
            />
            <p className="text-sm font-medium text-foreground">
              Start a new conversation
            </p>
            <p className="max-w-xs text-xs text-muted-foreground">
              Ask a question about your team&apos;s documents, workflows, or
              data.
            </p>
          </div>
        ) : (
          messages.map((message, index) => {
            const groupStart = isGroupStart(messages, index);
            const groupEnd = isGroupEnd(messages, index);

            return (
              <div
                key={message.id}
                className={
                  index === 0 ? undefined : groupStart ? "mt-4" : "mt-1"
                }
              >
                <MessageBubble
                  role={message.role}
                  content={message.content}
                  createdAt={message.createdAt}
                  showAvatar={groupStart}
                  showTimestamp={groupEnd}
                  isStreaming={message.id === streamingMessageId}
                  onRegenerate={() => onRegenerate(message.id)}
                  actionsDisabled={isBusy}
                />
              </div>
            );
          })
        )}
        {isLoading && (
          <div className={messages.length > 0 ? "mt-4" : undefined}>
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {showJumpToBottom && (
        <button
          type="button"
          onClick={jumpToBottom}
          aria-label="Scroll to latest messages"
          className="absolute bottom-4 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-popover transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
          New messages
        </button>
      )}
    </div>
  );
}
