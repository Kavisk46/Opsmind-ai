"use client";

import { CHART_COLORS } from "@/components/Charts";
import cpuUsageData from "@/lib/mock-data/analytics-cpu-usage.json";

import { sliceByRange } from "./analytics-utils";
import type { CpuUsagePoint, TimeRange } from "./types";
import { UsageChart } from "./UsageChart";

const data = cpuUsageData as CpuUsagePoint[];

interface CpuUsageChartProps {
  timeRange: TimeRange;
  isLoading?: boolean;
}

// CPU keeps the same color association as the Dashboard's own
// ResourceUtilizationChart (primary), so the two views stay visually
// consistent for the same metric.
export function CpuUsageChart({ timeRange, isLoading }: CpuUsageChartProps) {
  const points = sliceByRange(data, timeRange);

  return (
    <UsageChart
      title="CPU Usage"
      description={timeRange === "7d" ? "Last 7 days" : "Last 30 days"}
      data={points}
      series={[{ dataKey: "cpu", name: "CPU", color: CHART_COLORS.primary }]}
      unit="%"
      isLoading={isLoading}
    />
  );
}
