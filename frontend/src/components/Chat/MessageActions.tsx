"use client";

import { Check, Copy, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import { cn } from "@/lib/utils";

import type { MessageRole } from "./types";

interface MessageActionsProps {
  role: MessageRole;
  content: string;
  onRegenerate?: () => void;
  disabled?: boolean;
}

type Feedback = "like" | "dislike" | null;

const buttonClass =
  "inline-flex h-8 w-8 items-center justify-center rounded transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50";

export function MessageActions({
  role,
  content,
  onRegenerate,
  disabled = false,
}: MessageActionsProps) {
  const { copied, copy } = useCopyToClipboard();
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
      <button
        type="button"
        onClick={() => copy(content)}
        disabled={disabled}
        aria-label="Copy message"
        className={buttonClass}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <Copy className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </button>

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
