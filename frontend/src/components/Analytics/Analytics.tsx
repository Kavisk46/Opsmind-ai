"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { AnalyticsKpiCards } from "./AnalyticsKpiCards";
import { AnalyticsSection } from "./AnalyticsSection";
import { QueryLogSection } from "./QueryLogSection";
import { ResourceUsageSection } from "./ResourceUsageSection";
import { TimeRangeSelect } from "./TimeRangeSelect";
import { TopDocumentsCard } from "./TopDocumentsCard";
import type { TimeRange } from "./types";

// Dynamically imported so recharts (and each chart's own bundle weight)
// loads in its own chunk instead of the Analytics page's main bundle.
const ApiRequestsChart = dynamic(() =>
  import("./ApiRequestsChart").then((mod) => mod.ApiRequestsChart)
);
const QueryVolumeChart = dynamic(() =>
  import("./QueryVolumeChart").then((mod) => mod.QueryVolumeChart)
);
const ResponseTimeChart = dynamic(() =>
  import("./ResponseTimeChart").then((mod) => mod.ResponseTimeChart)
);
const TopCategoriesChart = dynamic(() =>
  import("./TopCategoriesChart").then((mod) => mod.TopCategoriesChart)
);

export function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>("7d");

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <TimeRangeSelect value={timeRange} onChange={setTimeRange} />
      </div>

      <AnalyticsSection
        title="Overview"
        description="Key metrics for the selected period"
      >
        <AnalyticsKpiCards timeRange={timeRange} />
      </AnalyticsSection>

      <AnalyticsSection
        title="Trends"
        description="Usage and performance over the selected period"
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
          <QueryVolumeChart timeRange={timeRange} />
          <ResponseTimeChart timeRange={timeRange} />
          <ApiRequestsChart timeRange={timeRange} />
          <TopCategoriesChart />
        </div>
      </AnalyticsSection>

      <ResourceUsageSection timeRange={timeRange} />

      <TopDocumentsCard />

      <QueryLogSection />
    </div>
  );
}
