"use client";

import { CHART_COLORS } from "@/components/Charts";
import networkUsageData from "@/lib/mock-data/analytics-network-usage.json";

import { sliceByRange } from "./analytics-utils";
import type { NetworkUsagePoint, TimeRange } from "./types";
import { UsageChart } from "./UsageChart";

const data = networkUsageData as NetworkUsagePoint[];

interface NetworkUsageChartProps {
  timeRange: TimeRange;
  isLoading?: boolean;
}

export function NetworkUsageChart({ timeRange, isLoading }: NetworkUsageChartProps) {
  const points = sliceByRange(data, timeRange);

  return (
    <UsageChart
      title="Network Usage"
      description={
        timeRange === "7d"
          ? "Inbound vs. outbound, last 7 days"
          : "Inbound vs. outbound, last 30 days"
      }
      data={points}
      series={[
        {
          dataKey: "inboundMbps",
          name: "Inbound",
          color: CHART_COLORS.info,
        },
        {
          dataKey: "outboundMbps",
          name: "Outbound",
          color: CHART_COLORS.success,
        },
      ]}
      unit=" Mbps"
      isLoading={isLoading}
    />
  );
}
