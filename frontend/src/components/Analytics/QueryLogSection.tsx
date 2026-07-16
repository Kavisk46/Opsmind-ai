"use client";

import { memo, useMemo, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import queryLogData from "@/lib/mock-data/analytics-query-log.json";

import { AnalyticsSection } from "./AnalyticsSection";
import { filterQueryLog } from "./query-log-utils";
import { QueryLogFilters } from "./QueryLogFilters";
import { QueryLogTable } from "./QueryLogTable";
import type { SelectFilterOption } from "./SelectFilter";
import type { DateRangeValue, QueryLogEntry, QueryLogStatus } from "./types";

const entries = queryLogData as QueryLogEntry[];

const DEFAULT_DATE_RANGE: DateRangeValue = {
  preset: "30d",
  start: null,
  end: null,
};

// Takes no props and owns all of its own state — memoized so it doesn't
// re-render when a sibling's state changes (e.g. the page-level time range
// toggling), which it doesn't depend on.
export const QueryLogSection = memo(function QueryLogSection() {
  const [category, setCategory] = useState<string | null>(null);
  const [status, setStatus] = useState<QueryLogStatus | null>(null);
  const [dateRange, setDateRange] = useState<DateRangeValue>(DEFAULT_DATE_RANGE);
  const isLoading = useSimulatedLoad();

  const categoryOptions = useMemo<SelectFilterOption[]>(() => {
    const unique = Array.from(
      new Set(entries.map((entry) => entry.category))
    ).sort();
    return unique.map((value) => ({ value, label: value }));
  }, []);

  const filtered = useMemo(
    () => filterQueryLog(entries, { category, status, dateRange }),
    [category, status, dateRange]
  );

  const hasActiveFilters =
    category !== null ||
    status !== null ||
    dateRange.preset !== DEFAULT_DATE_RANGE.preset ||
    dateRange.start !== null;

  const handleClearFilters = () => {
    setCategory(null);
    setStatus(null);
    setDateRange(DEFAULT_DATE_RANGE);
  };

  return (
    <AnalyticsSection
      title="Query Log"
      description="Recent AI queries with filters and date range"
    >
      <Card>
        <CardContent className="space-y-4 pt-4 sm:pt-6">
          <QueryLogFilters
            categoryOptions={categoryOptions}
            category={category}
            onCategoryChange={setCategory}
            status={status}
            onStatusChange={setStatus}
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            onClearFilters={handleClearFilters}
            hasActiveFilters={hasActiveFilters}
          />
          <QueryLogTable entries={filtered} isLoading={isLoading} />
        </CardContent>
      </Card>
    </AnalyticsSection>
  );
});
