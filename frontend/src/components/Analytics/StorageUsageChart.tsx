"use client";

import { CHART_COLORS } from "@/components/Charts";
import storageUsageData from "@/lib/mock-data/analytics-storage-usage.json";

import { sliceByRange } from "./analytics-utils";
import type { StorageUsagePoint, TimeRange } from "./types";
import { UsageChart } from "./UsageChart";

const data = storageUsageData as StorageUsagePoint[];

interface StorageUsageChartProps {
  timeRange: TimeRange;
  isLoading?: boolean;
}

export function StorageUsageChart({ timeRange, isLoading }: StorageUsageChartProps) {
  const points = sliceByRange(data, timeRange);

  return (
    <UsageChart
      title="Storage Usage"
      description={timeRange === "7d" ? "Last 7 days" : "Last 30 days"}
      data={points}
      series={[
        { dataKey: "storage", name: "Storage", color: CHART_COLORS.success },
      ]}
      unit="%"
      isLoading={isLoading}
    />
  );
}
