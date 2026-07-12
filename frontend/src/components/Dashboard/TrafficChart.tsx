"use client";

import { Line, LineChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import trafficData from "@/lib/mock-data/traffic.json";

interface TrafficPoint {
  day: string;
  visitors: number;
}

const data = trafficData as TrafficPoint[];

export function TrafficChart() {
  return (
    <ChartCard
      title="Traffic"
      description="Visitors over the last 7 days"
      chart={
        <LineChart
          data={data}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Line
            type="monotone"
            dataKey="visitors"
            stroke={CHART_COLORS.info}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      }
    >
      <AccessibleDataTable
        caption="Visitors by day, last 7 days"
        columns={["Day", "Visitors"]}
        rows={data.map((point) => [point.day, point.visitors])}
      />
    </ChartCard>
  );
}
