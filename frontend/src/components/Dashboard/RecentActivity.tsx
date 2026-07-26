"use client";

import { ActivityList, ActivityListItem } from "@/components/ActivityList";
import { Avatar } from "@/components/ui/avatar";
import type { BadgeProps } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { useRecentActivity, type ActivityEntry } from "./activity-api";

const BADGE_VARIANT_BY_TYPE: Record<ActivityEntry["type"], BadgeProps["variant"]> = {
  Upload: "info",
  AI: "success",
};

export function RecentActivity() {
  const { data: entries, isPending, error } = useRecentActivity();

  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Recent Activity</CardTitle>
        <CardDescription>Latest updates across your workspace</CardDescription>
      </CardHeader>
      <CardContent>
        {isPending && (
          <p className="text-sm text-muted-foreground">Loading activity…</p>
        )}
        {error && (
          <p className="text-sm text-muted-foreground">
            Couldn&apos;t load recent activity right now.
          </p>
        )}
        {entries && entries.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No activity yet — upload a document or start a conversation to
            see it here.
          </p>
        )}
        {entries && entries.length > 0 && (
          <ActivityList>
            {entries.map((entry) => (
              <ActivityListItem
                key={entry.id}
                leading={<Avatar name={entry.actor} size={32} />}
                title={
                  <>
                    <span className="font-medium">{entry.actor}</span>{" "}
                    {entry.action}{" "}
                    <span className="font-medium">{entry.target}</span>
                  </>
                }
                timestamp={entry.timestamp}
                badge={{
                  label: entry.type,
                  variant: BADGE_VARIANT_BY_TYPE[entry.type],
                }}
              />
            ))}
          </ActivityList>
        )}
      </CardContent>
    </Card>
  );
}
