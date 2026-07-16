"use client";

import { Legend, Line, LineChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import responseTimeData from "@/lib/mock-data/analytics-response-time.json";

import {
  computeTickInterval,
  formatShortDate,
  sliceByRange,
} from "./analytics-utils";
import type { ResponseTimePoint, TimeRange } from "./types";

const data = responseTimeData as ResponseTimePoint[];

interface ResponseTimeChartProps {
  timeRange: TimeRange;
}

export function ResponseTimeChart({ timeRange }: ResponseTimeChartProps) {
  const points = sliceByRange(data, timeRange);
  const interval = computeTickInterval(points.length);

  return (
    <ChartCard
      title="Response Time"
      description={
        timeRange === "7d"
          ? "Average vs. p95, last 7 days"
          : "Average vs. p95, last 30 days"
      }
      chart={
        <LineChart
          data={points}
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
          />
          <Legend
            wrapperStyle={{ fontSize: "0.75rem" }}
            iconType="circle"
            iconSize={8}
          />
          <Line
            type="monotone"
            dataKey="avgMs"
            name="Average"
            stroke={CHART_COLORS.info}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="p95Ms"
            name="p95"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      }
    >
      <AccessibleDataTable
        caption={`Response time in milliseconds by day, ${timeRange === "7d" ? "last 7 days" : "last 30 days"}`}
        columns={["Date", "Avg (ms)", "p95 (ms)"]}
        rows={points.map((point) => [point.date, point.avgMs, point.p95Ms])}
      />
    </ChartCard>
  );
}
