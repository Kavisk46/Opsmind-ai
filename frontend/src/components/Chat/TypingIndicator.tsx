import { MessageAvatar } from "./MessageAvatar";

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="h-8 w-8 shrink-0">
        <MessageAvatar role="assistant" />
      </div>
      <div className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2.5">
        <span className="sr-only">AI Assistant is typing</span>
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:-0.3s] motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:-0.15s] motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground motion-reduce:animate-none"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
