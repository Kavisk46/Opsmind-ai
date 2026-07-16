"use client";

import { Download, Layers, ListFilter } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toast } from "@/lib/toast";

import { DateRangePicker } from "./DateRangePicker";
import { SelectFilter, type SelectFilterOption } from "./SelectFilter";
import type { DateRangeValue, QueryLogStatus } from "./types";

const STATUS_OPTIONS: SelectFilterOption[] = [
  { value: "success", label: "Success" },
  { value: "error", label: "Error" },
  { value: "timeout", label: "Timeout" },
];

interface QueryLogFiltersProps {
  categoryOptions: SelectFilterOption[];
  category: string | null;
  onCategoryChange: (value: string | null) => void;
  status: QueryLogStatus | null;
  onStatusChange: (value: QueryLogStatus | null) => void;
  dateRange: DateRangeValue;
  onDateRangeChange: (value: DateRangeValue) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

export function QueryLogFilters({
  categoryOptions,
  category,
  onCategoryChange,
  status,
  onStatusChange,
  dateRange,
  onDateRangeChange,
  onClearFilters,
  hasActiveFilters,
}: QueryLogFiltersProps) {
  // UI placeholder only — no backend export exists yet, so this confirms
  // the click registered instead of leaving the button feeling dead.
  const handleExport = () => {
    toast("Export isn't available in this preview.");
  };

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <SelectFilter
          label="Category"
          icon={Layers}
          options={categoryOptions}
          value={category}
          onChange={onCategoryChange}
        />
        <SelectFilter
          label="Status"
          icon={ListFilter}
          options={STATUS_OPTIONS}
          value={status}
          onChange={(value) => onStatusChange(value as QueryLogStatus | null)}
        />
        <DateRangePicker value={dateRange} onChange={onDateRangeChange} />
        {hasActiveFilters && (
          <Button type="button" variant="ghost" size="sm" onClick={onClearFilters}>
            Clear filters
          </Button>
        )}
      </div>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleExport}
        className="gap-1.5"
      >
        <Download className="h-3.5 w-3.5" aria-hidden="true" />
        Export
      </Button>
    </div>
  );
}
