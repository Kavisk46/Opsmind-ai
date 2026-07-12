"use client";

import { Legend, Line, LineChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import resourceUtilizationData from "@/lib/mock-data/resource-utilization.json";

interface ResourcePoint {
  day: string;
  cpu: number;
  memory: number;
  network: number;
}

const data = resourceUtilizationData as ResourcePoint[];

export function ResourceUtilizationChart() {
  return (
    <ChartCard
      title="Resource Utilization"
      description="CPU, memory, and network — last 7 days"
      chart={
        <LineChart
          data={data}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Legend
            wrapperStyle={{ fontSize: "0.75rem" }}
            iconType="circle"
            iconSize={8}
          />
          <Line
            type="monotone"
            dataKey="cpu"
            name="CPU"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="memory"
            name="Memory"
            stroke={CHART_COLORS.warning}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="network"
            name="Network"
            stroke={CHART_COLORS.info}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      }
    >
      <AccessibleDataTable
        caption="Resource utilization percentage by day, last 7 days"
        columns={["Day", "CPU %", "Memory %", "Network %"]}
        rows={data.map((point) => [
          point.day,
          point.cpu,
          point.memory,
          point.network,
        ])}
      />
    </ChartCard>
  );
}
