"use client";

import { Calendar, ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { useDisclosure } from "@/hooks/use-disclosure";
import { cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

import { DATE_PRESET_OPTIONS, dateRangeLabel } from "./query-log-utils";
import type { DateRangeValue } from "./types";

interface DateRangePickerProps {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();
  const startInputId = useId();
  const endInputId = useId();

  const [draftStart, setDraftStart] = useState(value.start ?? "");
  const [draftEnd, setDraftEnd] = useState(value.end ?? "");

  // Reset the draft when opening rather than in an effect watching isOpen —
  // this is a direct response to the user's own click, not a side effect to
  // synchronize after the fact, so it belongs in the handler.
  const handleTriggerClick = () => {
    if (!isOpen) {
      setDraftStart(value.start ?? "");
      setDraftEnd(value.end ?? "");
    }
    toggle();
  };

  const selectPreset = (preset: DateRangeValue["preset"]) => {
    if (preset === "custom") {
      // Switches into custom mode and reveals the date inputs below,
      // without applying a filter until the user picks dates and confirms.
      onChange({ preset: "custom", start: draftStart || null, end: draftEnd || null });
      return;
    }
    onChange({ preset, start: null, end: null });
    close();
    triggerRef.current?.focus();
  };

  const applyCustomRange = () => {
    if (!draftStart || !draftEnd) {
      return;
    }
    onChange({ preset: "custom", start: draftStart, end: draftEnd });
    close();
    triggerRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={handleTriggerClick}
        aria-expanded={isOpen}
        aria-controls={panelId}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Calendar
          className="h-4 w-4 text-muted-foreground"
          aria-hidden="true"
        />
        {dateRangeLabel(value)}
        <ChevronDown
          className="h-3.5 w-3.5 text-muted-foreground"
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label="Filter by date range"
          className={cn(
            POPOVER_PANEL_CLASS,
            "absolute left-0 z-10 mt-2 w-64 p-1.5"
          )}
        >
          {DATE_PRESET_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-current={
                value.preset === option.value ? "true" : undefined
              }
              onClick={() => selectPreset(option.value)}
              className={cn(
                "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                value.preset === option.value && "font-medium text-foreground"
              )}
            >
              {option.label}
            </button>
          ))}

          {value.preset === "custom" && (
            <div className="mt-1 space-y-2 border-t border-border p-2.5">
              <div>
                <label
                  htmlFor={startInputId}
                  className="mb-1 block text-xs text-muted-foreground"
                >
                  Start date
                </label>
                <input
                  id={startInputId}
                  type="date"
                  value={draftStart}
                  onChange={(event) => setDraftStart(event.target.value)}
                  max={draftEnd || undefined}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div>
                <label
                  htmlFor={endInputId}
                  className="mb-1 block text-xs text-muted-foreground"
                >
                  End date
                </label>
                <input
                  id={endInputId}
                  type="date"
                  value={draftEnd}
                  onChange={(event) => setDraftEnd(event.target.value)}
                  min={draftStart || undefined}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <Button
                type="button"
                size="sm"
                className="w-full justify-center"
                disabled={!draftStart || !draftEnd}
                onClick={applyCustomRange}
              >
                Apply
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
