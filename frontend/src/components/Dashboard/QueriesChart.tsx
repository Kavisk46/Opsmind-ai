"use client";

import { Area, AreaChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import { queriesPerDaySeries } from "@/lib/mock-data/mockDashboard";

export function QueriesChart() {
  return (
    <ChartCard
      title="AI Queries"
      description="Questions asked over the last 7 days"
      chart={
        <AreaChart
          data={queriesPerDaySeries}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="queriesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.info} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_COLORS.info} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_COLORS.info}
            strokeWidth={2}
            fill="url(#queriesFill)"
          />
        </AreaChart>
      }
    >
      <AccessibleDataTable
        caption="AI queries per day, last 7 days"
        columns={["Day", "Queries"]}
        rows={queriesPerDaySeries.map((point) => [point.day, point.value])}
      />
    </ChartCard>
  );
}
