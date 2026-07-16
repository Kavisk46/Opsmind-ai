import { Bot, User } from "lucide-react";

import { cn } from "@/lib/utils";

import type { MessageRole } from "./types";

interface MessageAvatarProps {
  role: MessageRole;
}

export function MessageAvatar({ role }: MessageAvatarProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-full",
        isUser
          ? "bg-primary text-primary-foreground"
          : "bg-accent text-accent-foreground"
      )}
    >
      {isUser ? (
        <User className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Bot className="h-4 w-4" aria-hidden="true" />
      )}
    </div>
  );
}
