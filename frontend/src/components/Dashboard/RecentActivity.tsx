"use client";

import { useEffect, useState } from "react";

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
import { normalizeError } from "@/lib/api";

import { listRecentActivity, type ActivityEntry } from "./activity-api";

const BADGE_VARIANT_BY_TYPE: Record<ActivityEntry["type"], BadgeProps["variant"]> = {
  Upload: "info",
  AI: "success",
};

type FeedState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; entries: ActivityEntry[] };

export function RecentActivity() {
  const [state, setState] = useState<FeedState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    listRecentActivity({ signal: controller.signal })
      .then((entries) => setState({ status: "ready", entries }))
      .catch((error) => {
        if (normalizeError(error).code !== "ABORTED") {
          setState({ status: "error" });
        }
      });

    return () => controller.abort();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Recent Activity</CardTitle>
        <CardDescription>Latest updates across your workspace</CardDescription>
      </CardHeader>
      <CardContent>
        {state.status === "loading" && (
          <p className="text-sm text-muted-foreground">Loading activity…</p>
        )}
        {state.status === "error" && (
          <p className="text-sm text-muted-foreground">
            Couldn&apos;t load recent activity right now.
          </p>
        )}
        {state.status === "ready" && state.entries.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No activity yet — upload a document or start a conversation to
            see it here.
          </p>
        )}
        {state.status === "ready" && state.entries.length > 0 && (
          <ActivityList>
            {state.entries.map((entry) => (
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
