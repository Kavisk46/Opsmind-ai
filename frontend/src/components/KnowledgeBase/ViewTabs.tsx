"use client";

import { Clock, FileStack, Star, type LucideIcon } from "lucide-react";

import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import type { ViewMode } from "./types";

interface ViewTabsProps {
  value: ViewMode;
  onChange: (value: ViewMode) => void;
  favoritesCount: number;
  recentCount: number;
  controls?: string;
}

const TABS: { value: ViewMode; label: string; icon: LucideIcon }[] = [
  { value: "all", label: "All Documents", icon: FileStack },
  { value: "favorites", label: "Favorites", icon: Star },
  { value: "recent", label: "Recent", icon: Clock },
];

export function ViewTabs({
  value,
  onChange,
  favoritesCount,
  recentCount,
  controls,
}: ViewTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Document view"
      className="inline-flex items-center gap-1 rounded-md border border-border bg-card p-1"
    >
      {TABS.map((tab) => {
        const isActive = tab.value === value;
        const count =
          tab.value === "favorites"
            ? favoritesCount
            : tab.value === "recent"
              ? recentCount
              : undefined;

        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            id={`kb-tab-${tab.value}`}
            aria-selected={isActive}
            aria-controls={controls}
            onClick={() => onChange(tab.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors",
              FOCUS_RING_CLASS,
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <tab.icon className="h-4 w-4" aria-hidden="true" />
            {tab.label}
            {count !== undefined && (
              <span className="text-xs text-muted-foreground">({count})</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
