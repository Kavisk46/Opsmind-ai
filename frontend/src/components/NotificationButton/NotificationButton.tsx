"use client";

import { Bell } from "lucide-react";
import { useId } from "react";

import { useDisclosure } from "@/hooks/use-disclosure";
import { cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

interface NotificationButtonProps {
  count?: number;
}

export function NotificationButton({ count = 0 }: NotificationButtonProps) {
  const { isOpen, toggle, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();
  const hasBadge = count > 0;

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={
          hasBadge ? `Notifications, ${count} unread` : "Notifications"
        }
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Bell className="h-5 w-5" aria-hidden="true" />
        {hasBadge && (
          <span
            className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground"
            aria-hidden="true"
          >
            {count > 9 ? "9+" : count}
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
            "absolute right-0 mt-2 w-72 max-w-[calc(100vw-2rem)] p-4"
          )}
        >
          <p className="text-sm font-medium">Notifications</p>
          <p className="mt-2 text-sm text-muted-foreground">
            You&apos;re all caught up. Notifications will appear here.
          </p>
        </div>
      )}
    </div>
  );
}
