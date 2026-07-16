"use client";

import { ChevronDown, Tag as TagIcon } from "lucide-react";
import { useId } from "react";

import { useDisclosure } from "@/hooks/use-disclosure";
import { FOCUS_RING_CLASS, cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

import type { Tag } from "./types";

interface TagFilterProps {
  tags: Tag[];
  selectedTagIds: string[];
  onChange: (tagIds: string[]) => void;
}

export function TagFilter({ tags, selectedTagIds, onChange }: TagFilterProps) {
  const { isOpen, toggle, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();

  const toggleTag = (tagId: string) => {
    onChange(
      selectedTagIds.includes(tagId)
        ? selectedTagIds.filter((id) => id !== tagId)
        : [...selectedTagIds, tagId]
    );
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        className={cn(
          "inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent",
          FOCUS_RING_CLASS
        )}
      >
        <TagIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        Tags
        {selectedTagIds.length > 0 && (
          <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-xs font-medium text-primary-foreground">
            {selectedTagIds.length}
          </span>
        )}
        <ChevronDown
          className="h-3.5 w-3.5 text-muted-foreground"
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label="Filter by tag"
          className={cn(POPOVER_PANEL_CLASS, "absolute left-0 z-10 mt-2 w-64 p-2")}
        >
          <div className="flex flex-wrap gap-1.5">
            {tags.map((tag) => {
              const isSelected = selectedTagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => toggleTag(tag.id)}
                  className={cn(
                    "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                    FOCUS_RING_CLASS,
                    isSelected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background text-foreground hover:bg-accent"
                  )}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
