import { ClipboardButton } from "@/components/Clipboard";
import { MarkdownRenderer } from "@/components/Markdown";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

import { MessageActions } from "./MessageActions";
import { MessageAvatar } from "./MessageAvatar";
import type { Message } from "./types";

type MessageBubbleProps = Pick<
  Message,
  "role" | "content" | "createdAt" | "citations"
> & {
  showAvatar?: boolean;
  showTimestamp?: boolean;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  actionsDisabled?: boolean;
};

export function MessageBubble({
  role,
  content,
  createdAt,
  citations,
  showAvatar = true,
  showTimestamp = true,
  isStreaming = false,
  onRegenerate,
  actionsDisabled = false,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const time = formatDate(createdAt, { hour: "numeric", minute: "2-digit" });

  return (
    <div className={cn("flex items-start gap-3", isUser && "flex-row-reverse")}>
      <div className="h-8 w-8 shrink-0">
        {showAvatar && <MessageAvatar role={role} />}
      </div>
      <div
        className={cn(
          "max-w-[80%] sm:max-w-[70%]",
          isUser && "flex flex-col items-end"
        )}
      >
        <div
          className={cn(
            "rounded-lg px-3 py-2",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          )}
        >
          {isStreaming ? (
            <>
              <p className="text-sm whitespace-pre-wrap" aria-hidden="true">
                {content}
                <span
                  className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-text-bottom motion-reduce:animate-none"
                  aria-hidden="true"
                />
              </p>
              <span className="sr-only">AI Assistant is responding…</span>
            </>
          ) : (
            <MarkdownRenderer content={content} />
          )}
        </div>
        {!isStreaming && citations && citations.length > 0 && (
          <div className="mt-1 flex max-w-full items-start gap-1 text-xs text-muted-foreground">
            <p className="min-w-0">
              Sources:{" "}
              {citations
                .map((citation) =>
                  citation.pageNumber !== null
                    ? `${citation.documentName} (p.${citation.pageNumber})`
                    : citation.documentName
                )
                .join(", ")}
            </p>
            <ClipboardButton
              text={citations
                .map((citation, index) =>
                  citation.pageNumber !== null
                    ? `${index + 1}. ${citation.documentName} (p. ${citation.pageNumber})`
                    : `${index + 1}. ${citation.documentName}`
                )
                .join("\n")}
              ariaLabel="Copy sources"
              successMessage="Sources copied to clipboard"
              className="h-5 w-5 shrink-0"
            />
          </div>
        )}
        {showTimestamp && (
          <div
            className={cn(
              "mt-1 flex items-center gap-2",
              isUser && "flex-row-reverse"
            )}
          >
            {!isStreaming && (
              <span className="text-xs text-muted-foreground">{time}</span>
            )}
            <MessageActions
              role={role}
              content={content}
              onRegenerate={onRegenerate}
              disabled={actionsDisabled}
            />
          </div>
        )}
      </div>
    </div>
  );
}
