"use client";

import { Area, AreaChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import { storagePerDaySeries } from "@/lib/mock-data/mockDashboard";

export function StorageChart() {
  return (
    <ChartCard
      title="Storage"
      description="GB used over the last 7 days"
      chart={
        <AreaChart
          data={storagePerDaySeries}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="storageFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.warning} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_COLORS.warning} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_COLORS.warning}
            strokeWidth={2}
            fill="url(#storageFill)"
          />
        </AreaChart>
      }
    >
      <AccessibleDataTable
        caption="Storage used (GB) per day, last 7 days"
        columns={["Day", "Storage (GB)"]}
        rows={storagePerDaySeries.map((point) => [point.day, point.value])}
      />
    </ChartCard>
  );
}
