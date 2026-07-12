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
import recentActivityData from "@/lib/mock-data/recent-activity.json";

interface ActivityEntry {
  id: string;
  actor: string;
  action: string;
  target: string;
  type: string;
  timestamp: string;
}

const activity = recentActivityData as ActivityEntry[];

const BADGE_VARIANT_BY_TYPE: Record<string, BadgeProps["variant"]> = {
  Upload: "info",
  AI: "success",
  Report: "info",
  Index: "muted",
  Support: "success",
};

export function RecentActivity() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Latest updates across your workspace</CardDescription>
      </CardHeader>
      <CardContent>
        <ActivityList>
          {activity.map((entry) => (
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
                variant: BADGE_VARIANT_BY_TYPE[entry.type] ?? "muted",
              }}
            />
          ))}
        </ActivityList>
      </CardContent>
    </Card>
  );
}
