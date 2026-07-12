import type { ReactNode } from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import { formatRelativeTime } from "./format-relative-time";

interface ActivityListProps {
  children: ReactNode;
  className?: string;
}

export function ActivityList({ children, className }: ActivityListProps) {
  return <ul className={cn("space-y-4", className)}>{children}</ul>;
}

interface ActivityListItemProps {
  leading: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  timestamp: string;
  badge?: {
    label: string;
    variant: BadgeProps["variant"];
    className?: string;
  };
}

export function ActivityListItem({
  leading,
  title,
  description,
  timestamp,
  badge,
}: ActivityListItemProps) {
  return (
    <li className="flex items-start gap-3">
      <div className="shrink-0">{leading}</div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 text-sm text-foreground">{title}</div>
          {badge && (
            <Badge variant={badge.variant} className={badge.className}>
              {badge.label}
            </Badge>
          )}
        </div>
        {description && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {description}
          </p>
        )}
        <p className="mt-0.5 text-xs text-muted-foreground">
          <time dateTime={timestamp}>{formatRelativeTime(timestamp)}</time>
        </p>
      </div>
    </li>
  );
}
