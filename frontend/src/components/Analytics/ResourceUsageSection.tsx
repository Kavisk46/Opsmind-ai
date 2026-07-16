"use client";

import { useSimulatedLoad } from "@/hooks/use-simulated-load";

import { AnalyticsSection } from "./AnalyticsSection";
import { CpuUsageChart } from "./CpuUsageChart";
import { MemoryUsageChart } from "./MemoryUsageChart";
import { NetworkUsageChart } from "./NetworkUsageChart";
import { StorageUsageChart } from "./StorageUsageChart";
import type { TimeRange } from "./types";

interface ResourceUsageSectionProps {
  timeRange: TimeRange;
}

export function ResourceUsageSection({ timeRange }: ResourceUsageSectionProps) {
  const isLoading = useSimulatedLoad();

  return (
    <AnalyticsSection
      title="Resource Usage"
      description="Infrastructure utilization over the selected period"
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CpuUsageChart timeRange={timeRange} isLoading={isLoading} />
        <MemoryUsageChart timeRange={timeRange} isLoading={isLoading} />
        <NetworkUsageChart timeRange={timeRange} isLoading={isLoading} />
        <StorageUsageChart timeRange={timeRange} isLoading={isLoading} />
      </div>
    </AnalyticsSection>
  );
}
