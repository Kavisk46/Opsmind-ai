"use client";

import { Area, AreaChart, Legend, ResponsiveContainer, Tooltip, XAxis } from "recharts";

import { AccessibleDataTable, CHART_AXIS_PROPS, CHART_TOOLTIP_STYLE } from "@/components/Charts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { computeTickInterval, formatShortDate } from "./analytics-utils";

export interface UsageChartSeries<T> {
  dataKey: keyof T & string;
  name: string;
  color: string;
}

interface UsageChartProps<T extends { date: string }> {
  title: string;
  description?: string;
  data: T[];
  series: UsageChartSeries<T>[];
  unit?: string;
  isLoading?: boolean;
}

// Generic, reusable time-series usage chart. CPU/Memory/Network/Storage each
// render through this one wrapper — passing their own data + series config —
// instead of four near-duplicate chart components. Generic over the data
// point type so a series' dataKey is checked against the actual data shape
// at each call site (a typo'd key is a compile error, not a silent no-op),
// with no unsafe casts needed to bridge the two. Not built on the existing
// ChartCard (which always expects a real chart element) because loading and
// empty states need to swap out the chart body entirely; it does reuse
// ChartCard's underlying pieces (Card primitives, AccessibleDataTable,
// ResponsiveContainer, chart-theme tokens).
export function UsageChart<T extends { date: string }>({
  title,
  description,
  data,
  series,
  unit = "",
  isLoading = false,
}: UsageChartProps<T>) {
  const interval = computeTickInterval(data.length);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-64">
          {isLoading ? (
            <div role="status" aria-label={`Loading ${title}`} className="h-full">
              <Skeleton className="h-full w-full" />
            </div>
          ) : data.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
              <p className="text-sm font-medium text-foreground">
                No data available
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                There&apos;s no {title.toLowerCase()} data for this period yet.
              </p>
            </div>
          ) : (
            <div aria-hidden="true" className="h-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={data}
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="date"
                    {...CHART_AXIS_PROPS}
                    tickFormatter={formatShortDate}
                    interval={interval}
                  />
                  <Tooltip
                    contentStyle={CHART_TOOLTIP_STYLE}
                    labelFormatter={formatShortDate}
                    formatter={(value: unknown) =>
                      typeof value === "number" ? `${value}${unit}` : ""
                    }
                  />
                  {series.length > 1 && (
                    <Legend
                      wrapperStyle={{ fontSize: "0.75rem" }}
                      iconType="circle"
                      iconSize={8}
                    />
                  )}
                  {series.map((s) => (
                    <Area
                      key={s.dataKey}
                      type="monotone"
                      // Recharts infers its own generic from `data` here,
                      // which doesn't line up with UsageChart's — `dataKey`
                      // is always a plain string at runtime regardless.
                      dataKey={s.dataKey as string}
                      name={s.name}
                      stroke={s.color}
                      strokeWidth={2}
                      fill={s.color}
                      fillOpacity={0.1}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        {!isLoading && data.length > 0 && (
          <AccessibleDataTable
            caption={`${title} by day`}
            columns={["Date", ...series.map((s) => s.name)]}
            rows={data.map((point) => [
              point.date,
              // Safe in practice: every UsageChart data point is dates plus
              // plain numbers (see CpuUsagePoint et al.) — the generic
              // constraint only guarantees `date`, so TS can't confirm the
              // rest without a broader Record constraint that would in turn
              // break inference for plain interfaces at the call sites.
              ...series.map((s) => point[s.dataKey] as string | number),
            ])}
          />
        )}
      </CardContent>
    </Card>
  );
}
