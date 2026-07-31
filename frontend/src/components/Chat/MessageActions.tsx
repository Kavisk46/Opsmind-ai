"use client";

import { RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ClipboardButton, ClipboardMenu } from "@/components/Clipboard";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import type { MessageRole } from "./types";

interface MessageActionsProps {
  role: MessageRole;
  content: string;
  onRegenerate?: () => void;
  disabled?: boolean;
}

type Feedback = "like" | "dislike" | null;

const buttonClass = cn(
  "inline-flex h-8 w-8 items-center justify-center rounded transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50",
  FOCUS_RING_CLASS
);

export function MessageActions({
  role,
  content,
  onRegenerate,
  disabled = false,
}: MessageActionsProps) {
  const [feedback, setFeedback] = useState<Feedback>(null);
  const isAssistant = role === "assistant";

  // A regenerate resets this message's content to "" before streaming the
  // replacement in — that transition (rather than a remount) is what should
  // clear out feedback left over from the previous answer.
  const previousContentRef = useRef(content);
  useEffect(() => {
    if (content === "" && previousContentRef.current !== "") {
      setFeedback(null);
    }
    previousContentRef.current = content;
  }, [content]);

  return (
    <div className="flex items-center gap-1 text-muted-foreground">
      {isAssistant ? (
        // Assistant replies are markdown (see MessageBubble's
        // MarkdownRenderer) — worth offering both a Markdown-source copy
        // and a plain-text copy, unlike a user's own message below.
        <ClipboardMenu markdown={content} ariaLabel="Copy message" disabled={disabled} />
      ) : (
        <ClipboardButton
          text={content}
          ariaLabel="Copy message"
          disabled={disabled}
          className={buttonClass}
        />
      )}

      {isAssistant && (
        <>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={disabled}
            aria-label="Regenerate response"
            className={buttonClass}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() =>
              setFeedback((prev) => (prev === "like" ? null : "like"))
            }
            aria-label="Good response"
            aria-pressed={feedback === "like"}
            className={cn(
              buttonClass,
              feedback === "like" && "bg-accent text-accent-foreground"
            )}
          >
            <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() =>
              setFeedback((prev) => (prev === "dislike" ? null : "dislike"))
            }
            aria-label="Bad response"
            aria-pressed={feedback === "dislike"}
            className={cn(
              buttonClass,
              feedback === "dislike" && "bg-accent text-accent-foreground"
            )}
          >
            <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </>
      )}
    </div>
  );
}
