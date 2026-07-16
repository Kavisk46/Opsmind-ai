"use client";

import { X } from "lucide-react";
import { useRef } from "react";

import { useModalDismiss } from "@/hooks/use-modal-dismiss";
import { cn } from "@/lib/utils";

import type { SettingsSection } from "./types";

interface SettingsNavProps {
  sections: SettingsSection[];
  activeSectionId: string;
  onSelectSection: (id: string) => void;
  // Provided only by the mobile modal instance — matches the onClose
  // pattern used throughout (Chat's ConversationList, Knowledge Base's
  // FolderTree): close button, Escape, body-scroll lock, focus-on-open.
  onClose?: () => void;
}

export function SettingsNav({
  sections,
  activeSectionId,
  onSelectSection,
  onClose,
}: SettingsNavProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useModalDismiss({ onClose, closeButtonRef, containerRef });

  return (
    <div
      ref={containerRef}
      className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-border bg-card lg:h-[calc(100vh-14rem)] lg:w-64 lg:shrink-0"
    >
      <div className="flex items-center justify-between gap-2 border-b border-border p-3">
        <h2 className="text-sm font-semibold text-foreground">Settings</h2>
        {onClose && (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close settings navigation"
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      <nav
        aria-label="Settings sections"
        className="flex-1 space-y-0.5 overflow-y-auto p-2"
      >
        {sections.map((section) => {
          const isActive = section.id === activeSectionId;
          return (
            <button
              key={section.id}
              type="button"
              onClick={() => onSelectSection(section.id)}
              aria-current={isActive ? "true" : undefined}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <section.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">{section.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
