"use client";

import { Bar, BarChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import apiUsageData from "@/lib/mock-data/api-usage.json";

interface ApiUsagePoint {
  day: string;
  requests: number;
}

const data = apiUsageData as ApiUsagePoint[];

export function ApiUsageChart() {
  return (
    <ChartCard
      title="API Usage"
      description="Requests over the last 7 days"
      chart={
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={false} />
          <Bar
            dataKey="requests"
            fill={CHART_COLORS.success}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      }
    >
      <AccessibleDataTable
        caption="API requests by day, last 7 days"
        columns={["Day", "Requests"]}
        rows={data.map((point) => [point.day, point.requests])}
      />
    </ChartCard>
  );
}
