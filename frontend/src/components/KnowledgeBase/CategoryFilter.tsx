"use client";

import { Check, ChevronDown, LayoutGrid } from "lucide-react";
import { useId } from "react";

import { useDisclosure } from "@/hooks/use-disclosure";
import {
  FOCUS_RING_CLASS,
  POPOVER_ITEM_CLASS,
  POPOVER_PANEL_CLASS,
  cn,
} from "@/lib/utils";

import type { Category } from "./types";

interface CategoryFilterProps {
  categories: Category[];
  selectedCategoryId: string | null;
  onChange: (categoryId: string | null) => void;
}

export function CategoryFilter({
  categories,
  selectedCategoryId,
  onChange,
}: CategoryFilterProps) {
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();

  const selectedLabel = selectedCategoryId
    ? (categories.find((category) => category.id === selectedCategoryId)
        ?.name ?? "Category")
    : "All categories";

  const select = (categoryId: string | null) => {
    onChange(categoryId);
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
        className={cn(
          "inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent",
          FOCUS_RING_CLASS
        )}
      >
        <LayoutGrid
          className="h-4 w-4 text-muted-foreground"
          aria-hidden="true"
        />
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
          aria-label="Filter by category"
          className={cn(POPOVER_PANEL_CLASS, "absolute left-0 z-10 mt-2 w-56 p-1.5")}
        >
          <button
            type="button"
            aria-current={selectedCategoryId === null ? "true" : undefined}
            onClick={() => select(null)}
            className={cn(
              POPOVER_ITEM_CLASS,
              FOCUS_RING_CLASS,
              selectedCategoryId === null && "font-medium text-foreground"
            )}
          >
            All categories
            {selectedCategoryId === null && (
              <Check className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
          {categories.map((category) => (
            <button
              key={category.id}
              type="button"
              aria-current={
                selectedCategoryId === category.id ? "true" : undefined
              }
              onClick={() => select(category.id)}
              className={cn(
                POPOVER_ITEM_CLASS,
                FOCUS_RING_CLASS,
                selectedCategoryId === category.id &&
                  "font-medium text-foreground"
              )}
            >
              {category.name}
              {selectedCategoryId === category.id && (
                <Check className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
