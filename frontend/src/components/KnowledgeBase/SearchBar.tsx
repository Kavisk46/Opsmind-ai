"use client";

import { Search } from "lucide-react";

import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative flex-1">
      <label htmlFor="kb-search" className="sr-only">
        Search documents
      </label>
      <Search
        className="pointer-events-none absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <input
        id="kb-search"
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search documents…"
        className={cn(
          "w-full rounded-md border border-border bg-background py-2 pr-3 pl-8 text-sm text-foreground placeholder:text-muted-foreground",
          FOCUS_RING_CLASS
        )}
      />
    </div>
  );
}
