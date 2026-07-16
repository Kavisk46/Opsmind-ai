"use client";

import { CHART_COLORS } from "@/components/Charts";
import memoryUsageData from "@/lib/mock-data/analytics-memory-usage.json";

import { sliceByRange } from "./analytics-utils";
import type { MemoryUsagePoint, TimeRange } from "./types";
import { UsageChart } from "./UsageChart";

const data = memoryUsageData as MemoryUsagePoint[];

interface MemoryUsageChartProps {
  timeRange: TimeRange;
  isLoading?: boolean;
}

// Matches the Dashboard's ResourceUtilizationChart, which already uses
// warning for memory.
export function MemoryUsageChart({ timeRange, isLoading }: MemoryUsageChartProps) {
  const points = sliceByRange(data, timeRange);

  return (
    <UsageChart
      title="Memory Usage"
      description={timeRange === "7d" ? "Last 7 days" : "Last 30 days"}
      data={points}
      series={[
        { dataKey: "memory", name: "Memory", color: CHART_COLORS.warning },
      ]}
      unit="%"
      isLoading={isLoading}
    />
  );
}
