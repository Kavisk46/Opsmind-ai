import { formatDate } from "@/lib/format";

import type { TimeRange } from "./types";

function rangeDays(range: TimeRange): number {
  return range === "7d" ? 7 : 30;
}

export function sliceByRange<T>(data: T[], range: TimeRange): T[] {
  return data.slice(-rangeDays(range));
}

// The window immediately before the current one, same length — e.g. for
// "7d" this is the 7 days before the last 7. Requires at least 2x the
// range's length of underlying history to return anything meaningful.
export function previousPeriodSlice<T>(data: T[], range: TimeRange): T[] {
  const days = rangeDays(range);
  return data.slice(-(days * 2), -days);
}

export function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

export function average(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return sum(values) / values.length;
}

// Positive = current is higher than previous. Callers decide whether that's
// "good" (e.g. query volume) or "bad" (e.g. response time) for isPositive.
export function percentChange(current: number, previous: number): number {
  if (previous === 0) {
    return 0;
  }
  return ((current - previous) / previous) * 100;
}

// Shared X-axis tick formatter for every day-by-day time-series chart —
// Recharts passes tick/label values through as ReactNode | undefined, not
// just string, hence the runtime guard.
export function formatShortDate(value: unknown): string {
  if (typeof value !== "string") {
    return "";
  }
  return formatDate(value, { month: "short", day: "numeric" });
}

// Roughly N labels across the axis regardless of how many points are
// plotted, so a 30-day chart doesn't try to label every single day.
export function computeTickInterval(pointCount: number): number {
  return Math.max(0, Math.ceil(pointCount / 7) - 1);
}
