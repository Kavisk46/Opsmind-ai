import { MessagesSquare, Pin } from "lucide-react";
import Link from "next/link";

import { formatRelativeTime } from "@/components/ActivityList";
import { Avatar } from "@/components/ui/avatar";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { recentConversations } from "@/lib/mock-data/mockDashboard";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

interface RecentConversationsProps {
  className?: string;
}

export function RecentConversations({ className }: RecentConversationsProps) {
  return (
    <FadeIn className={className} delay={0.05}>
      <Card className="flex h-full flex-col">
        <CardHeader className="flex-row items-start justify-between">
          <div>
            <CardTitle level="h2">Recent Conversations</CardTitle>
            <CardDescription>What your team has been asking</CardDescription>
          </div>
          <Link
            href="/assistant"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
          >
            View all
          </Link>
        </CardHeader>

        {recentConversations.length === 0 ? (
          <div className="px-4 pb-6 sm:px-6">
            <EmptyState
              icon={MessagesSquare}
              title="No conversations yet"
              description="Ask your AI assistant a question to start your first conversation."
            />
          </div>
        ) : (
          <ul className="space-y-1 px-2 pb-2 sm:px-3 sm:pb-3">
            {recentConversations.map((conversation) => (
              <li key={conversation.id}>
                <Link
                  href="/assistant"
                  className="flex items-start gap-3 rounded-md p-2.5 transition-colors hover:bg-accent/50"
                >
                  <Avatar name={conversation.participant} size={36} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="truncate text-sm font-medium text-foreground">
                        {conversation.title}
                      </p>
                      {conversation.pinned && (
                        <Pin
                          className="h-3 w-3 shrink-0 text-primary"
                          aria-label="Pinned"
                        />
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      {conversation.lastMessage}
                    </p>
                  </div>
                  <time
                    dateTime={conversation.updatedAt}
                    className="shrink-0 pt-0.5 text-xs text-muted-foreground"
                  >
                    {formatRelativeTime(conversation.updatedAt)}
                  </time>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </FadeIn>
  );
}
