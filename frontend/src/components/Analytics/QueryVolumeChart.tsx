"use client";

import { Area, AreaChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import queryVolumeData from "@/lib/mock-data/analytics-query-volume.json";

import {
  computeTickInterval,
  formatShortDate,
  sliceByRange,
} from "./analytics-utils";
import type { QueryVolumePoint, TimeRange } from "./types";

const data = queryVolumeData as QueryVolumePoint[];

interface QueryVolumeChartProps {
  timeRange: TimeRange;
}

export function QueryVolumeChart({ timeRange }: QueryVolumeChartProps) {
  const points = sliceByRange(data, timeRange);
  const interval = computeTickInterval(points.length);

  return (
    <ChartCard
      title="AI Query Volume"
      description={timeRange === "7d" ? "Last 7 days" : "Last 30 days"}
      chart={
        <AreaChart
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
          <Area
            type="monotone"
            dataKey="queries"
            stroke={CHART_COLORS.info}
            strokeWidth={2}
            fill={CHART_COLORS.info}
            fillOpacity={0.1}
          />
        </AreaChart>
      }
    >
      <AccessibleDataTable
        caption={`AI query volume by day, ${timeRange === "7d" ? "last 7 days" : "last 30 days"}`}
        columns={["Date", "Queries"]}
        rows={points.map((point) => [point.date, point.queries])}
      />
    </ChartCard>
  );
}
