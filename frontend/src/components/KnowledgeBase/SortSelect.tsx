"use client";

import { ArrowUpDown, Check } from "lucide-react";
import { useId } from "react";

import { useDisclosure } from "@/hooks/use-disclosure";
import { cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

import { SORT_OPTIONS } from "./document-filters";
import type { SortOption } from "./types";

interface SortSelectProps {
  value: SortOption;
  onChange: (value: SortOption) => void;
}

export function SortSelect({ value, onChange }: SortSelectProps) {
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();

  const selectedLabel =
    SORT_OPTIONS.find((option) => option.value === value)?.label ?? "Sort";

  const select = (option: SortOption) => {
    onChange(option);
    close();
    triggerRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowUpDown
          className="h-4 w-4 text-muted-foreground"
          aria-hidden="true"
        />
        {selectedLabel}
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label="Sort documents"
          className={cn(POPOVER_PANEL_CLASS, "absolute right-0 z-10 mt-2 w-56 p-1.5")}
        >
          {SORT_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-current={value === option.value ? "true" : undefined}
              onClick={() => select(option.value)}
              className={cn(
                "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                value === option.value && "font-medium text-foreground"
              )}
            >
              {option.label}
              {value === option.value && (
                <Check className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
