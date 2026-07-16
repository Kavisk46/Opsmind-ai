import type { DateRangeValue, QueryLogEntry, QueryLogStatus } from "./types";

export const DATE_PRESET_OPTIONS: { value: DateRangeValue["preset"]; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "custom", label: "Custom range" },
];

function startOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function endOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(23, 59, 59, 999);
  return copy;
}

// Resolves a preset (or custom start/end) to concrete boundaries. Returns
// null when there's nothing to filter by yet — a "custom" preset with one
// or both dates unset — callers treat that as "show everything".
export function resolveDateRange(
  value: DateRangeValue
): { start: Date; end: Date } | null {
  const now = new Date();
  const today = endOfDay(now);

  switch (value.preset) {
    case "today":
      return { start: startOfDay(now), end: today };
    case "7d": {
      const start = startOfDay(now);
      start.setDate(start.getDate() - 6);
      return { start, end: today };
    }
    case "30d": {
      const start = startOfDay(now);
      start.setDate(start.getDate() - 29);
      return { start, end: today };
    }
    case "90d": {
      const start = startOfDay(now);
      start.setDate(start.getDate() - 89);
      return { start, end: today };
    }
    case "custom": {
      if (!value.start || !value.end) {
        return null;
      }
      return {
        start: startOfDay(new Date(`${value.start}T00:00:00`)),
        end: endOfDay(new Date(`${value.end}T00:00:00`)),
      };
    }
  }
}

export function dateRangeLabel(value: DateRangeValue): string {
  if (value.preset !== "custom") {
    return (
      DATE_PRESET_OPTIONS.find((option) => option.value === value.preset)
        ?.label ?? "Date range"
    );
  }
  if (!value.start || !value.end) {
    return "Custom range";
  }
  return `${value.start} – ${value.end}`;
}

interface FilterQueryLogOptions {
  category: string | null;
  status: QueryLogStatus | null;
  dateRange: DateRangeValue;
}

export function filterQueryLog(
  entries: QueryLogEntry[],
  { category, status, dateRange }: FilterQueryLogOptions
): QueryLogEntry[] {
  const range = resolveDateRange(dateRange);

  return entries.filter((entry) => {
    if (category && entry.category !== category) {
      return false;
    }
    if (status && entry.status !== status) {
      return false;
    }
    if (range) {
      const entryDate = new Date(entry.timestamp);
      if (entryDate < range.start || entryDate > range.end) {
        return false;
      }
    }
    return true;
  });
}
