"use client";

import {
  Bell,
  CheckCircle2,
  Info,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { useId } from "react";

import { ActivityList, ActivityListItem } from "@/components/ActivityList";
import type { BadgeProps } from "@/components/ui/badge";
import { useDisclosure } from "@/hooks/use-disclosure";
import notificationsData from "@/lib/mock-data/notifications.json";
import { FOCUS_RING_CLASS, cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

type NotificationStatus = "info" | "success" | "warning";

interface NotificationEntry {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  status: NotificationStatus;
  read: boolean;
}

const notifications = notificationsData as NotificationEntry[];

const STATUS_ICON: Record<NotificationStatus, LucideIcon> = {
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
};

const STATUS_ICON_CLASS: Record<NotificationStatus, string> = {
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
};

const STATUS_BADGE_VARIANT: Record<NotificationStatus, BadgeProps["variant"]> =
  {
    info: "info",
    success: "success",
    warning: "warning",
  };

export function NotificationButton() {
  const { isOpen, toggle, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();
  const unreadCount = notifications.filter((n) => !n.read).length;
  const hasBadge = unreadCount > 0;

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={
          hasBadge ? `Notifications, ${unreadCount} unread` : "Notifications"
        }
        className={cn(
          "relative inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
          FOCUS_RING_CLASS
        )}
      >
        <Bell className="h-5 w-5" aria-hidden="true" />
        {hasBadge && (
          <span
            className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground"
            aria-hidden="true"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label="Notifications"
          className={cn(
            POPOVER_PANEL_CLASS,
            "absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] p-4"
          )}
        >
          <p className="text-sm font-medium text-foreground">Notifications</p>
          <div className="mt-3">
            <ActivityList>
              {notifications.map((notification) => {
                const StatusIcon = STATUS_ICON[notification.status];
                return (
                  <ActivityListItem
                    key={notification.id}
                    leading={
                      <StatusIcon
                        className={cn(
                          "h-5 w-5",
                          STATUS_ICON_CLASS[notification.status]
                        )}
                        aria-hidden="true"
                      />
                    }
                    title={
                      <span
                        className={cn(
                          !notification.read && "font-medium text-foreground"
                        )}
                      >
                        {notification.title}
                      </span>
                    }
                    description={notification.description}
                    timestamp={notification.timestamp}
                    badge={{
                      label: notification.status,
                      variant: STATUS_BADGE_VARIANT[notification.status],
                      className: "capitalize",
                    }}
                  />
                );
              })}
            </ActivityList>
          </div>
        </div>
      )}
    </div>
  );
}
