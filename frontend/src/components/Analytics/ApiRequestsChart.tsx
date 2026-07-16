"use client";

import { Bar, BarChart, Legend, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import apiRequestsData from "@/lib/mock-data/analytics-api-requests.json";

import {
  computeTickInterval,
  formatShortDate,
  sliceByRange,
} from "./analytics-utils";
import type { ApiRequestPoint, TimeRange } from "./types";

const data = apiRequestsData as ApiRequestPoint[];

interface ApiRequestsChartProps {
  timeRange: TimeRange;
}

// Success/error is a status encoding (good vs. critical), so it deliberately
// reuses the app's existing success/destructive tokens rather than a
// generic categorical color — the same tokens badges and StatCard trends
// already use for "good" and "bad" everywhere else in the app.
export function ApiRequestsChart({ timeRange }: ApiRequestsChartProps) {
  const points = sliceByRange(data, timeRange);
  const interval = computeTickInterval(points.length);

  return (
    <ChartCard
      title="API Requests"
      description={
        timeRange === "7d"
          ? "Success vs. error, last 7 days"
          : "Success vs. error, last 30 days"
      }
      chart={
        <BarChart
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
            cursor={false}
            labelFormatter={formatShortDate}
          />
          <Legend
            wrapperStyle={{ fontSize: "0.75rem" }}
            iconType="circle"
            iconSize={8}
          />
          <Bar
            dataKey="success"
            name="Success"
            stackId="requests"
            fill={CHART_COLORS.success}
          />
          <Bar
            dataKey="error"
            name="Error"
            stackId="requests"
            fill={CHART_COLORS.destructive}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      }
    >
      <AccessibleDataTable
        caption={`API requests by day, ${timeRange === "7d" ? "last 7 days" : "last 30 days"}`}
        columns={["Date", "Success", "Error"]}
        rows={points.map((point) => [point.date, point.success, point.error])}
      />
    </ChartCard>
  );
}
