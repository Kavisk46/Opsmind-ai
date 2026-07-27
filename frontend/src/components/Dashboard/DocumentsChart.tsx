"use client";

import { Bar, BarChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import { documentsPerDaySeries } from "@/lib/mock-data/mockDashboard";

export function DocumentsChart() {
  return (
    <ChartCard
      title="Documents per Day"
      description="Uploaded over the last 7 days"
      chart={
        <BarChart
          data={documentsPerDaySeries}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Bar dataKey="value" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
        </BarChart>
      }
    >
      <AccessibleDataTable
        caption="Documents uploaded per day, last 7 days"
        columns={["Day", "Documents"]}
        rows={documentsPerDaySeries.map((point) => [point.day, point.value])}
      />
    </ChartCard>
  );
}
