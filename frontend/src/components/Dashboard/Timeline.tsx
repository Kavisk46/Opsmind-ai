import {
  Bot,
  FolderPlus,
  Network,
  UploadCloud,
  UserPlus,
  type LucideIcon,
} from "lucide-react";

import { ActivityList, ActivityListItem } from "@/components/ActivityList";
import type { BadgeProps } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { timelineEntries, type ActivityKind } from "@/lib/mock-data/mockDashboard";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

const KIND_ICON: Record<ActivityKind, LucideIcon> = {
  upload: UploadCloud,
  ai: Bot,
  invite: UserPlus,
  collection: FolderPlus,
  embedding: Network,
};

const KIND_BADGE: Record<ActivityKind, { label: string; variant: BadgeProps["variant"] }> = {
  upload: { label: "Upload", variant: "info" },
  ai: { label: "AI", variant: "success" },
  invite: { label: "Team", variant: "warning" },
  collection: { label: "Collection", variant: "muted" },
  embedding: { label: "Embedding", variant: "success" },
};

const KIND_ICON_CLASS: Record<ActivityKind, string> = {
  upload: "bg-info/15 text-info",
  ai: "bg-success/15 text-success",
  invite: "bg-warning/15 text-warning",
  collection: "bg-muted text-muted-foreground",
  embedding: "bg-success/15 text-success",
};

interface TimelineProps {
  className?: string;
}

export function Timeline({ className }: TimelineProps) {
  return (
    <FadeIn className={className} delay={0.1}>
      <Card>
        <CardHeader>
          <CardTitle level="h2">Activity Timeline</CardTitle>
          <CardDescription>Everything happening across your workspace</CardDescription>
        </CardHeader>

        {timelineEntries.length === 0 ? (
          <div className="px-4 pb-6 sm:px-6">
            <EmptyState
              icon={Network}
              title="No activity yet"
              description="Uploads, AI answers, and team changes will show up here."
            />
          </div>
        ) : (
          <div className="px-4 pb-6 sm:px-6">
            <ActivityList>
              {timelineEntries.map((entry) => {
                const Icon = KIND_ICON[entry.kind];
                const badge = KIND_BADGE[entry.kind];
                return (
                  <ActivityListItem
                    key={entry.id}
                    leading={
                      <span
                        className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-full",
                          KIND_ICON_CLASS[entry.kind]
                        )}
                      >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </span>
                    }
                    title={
                      <>
                        <span className="font-medium">{entry.actor}</span>{" "}
                        {entry.action}{" "}
                        <span className="font-medium">{entry.target}</span>
                      </>
                    }
                    timestamp={entry.timestamp}
                    badge={badge}
                  />
                );
              })}
            </ActivityList>
          </div>
        )}
      </Card>
    </FadeIn>
  );
}
