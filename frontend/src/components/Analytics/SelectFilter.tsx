"use client";

import { Check, ChevronDown, type LucideIcon } from "lucide-react";
import { useId } from "react";

import { useDisclosure } from "@/hooks/use-disclosure";
import { cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

export interface SelectFilterOption {
  value: string;
  label: string;
}

interface SelectFilterProps {
  label: string;
  icon: LucideIcon;
  options: SelectFilterOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  allLabel?: string;
}

// Generic single-select dropdown filter — the same disclosure pattern used
// throughout the app (see UserProfileDropdown, Knowledge Base's
// CategoryFilter), generalized so both the category and status filters
// here render through this one component instead of two near-duplicates.
export function SelectFilter({
  label,
  icon: Icon,
  options,
  value,
  onChange,
  allLabel = `All ${label.toLowerCase()}`,
}: SelectFilterProps) {
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();

  const selectedLabel = value
    ? (options.find((option) => option.value === value)?.label ?? label)
    : allLabel;

  const select = (next: string | null) => {
    onChange(next);
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
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        {selectedLabel}
        <ChevronDown
          className="h-3.5 w-3.5 text-muted-foreground"
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label={`Filter by ${label.toLowerCase()}`}
          className={cn(
            POPOVER_PANEL_CLASS,
            "absolute left-0 z-10 mt-2 w-56 p-1.5"
          )}
        >
          <button
            type="button"
            aria-current={value === null ? "true" : undefined}
            onClick={() => select(null)}
            className={cn(
              "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === null && "font-medium text-foreground"
            )}
          >
            {allLabel}
            {value === null && (
              <Check className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
          {options.map((option) => (
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
