import dynamic from "next/dynamic";

// Dynamically imported so recharts (and each chart's own bundle weight)
// loads in its own chunk instead of the Dashboard's main bundle.
const ApiUsageChart = dynamic(() =>
  import("./ApiUsageChart").then((mod) => mod.ApiUsageChart)
);
const ResourceUtilizationChart = dynamic(() =>
  import("./ResourceUtilizationChart").then(
    (mod) => mod.ResourceUtilizationChart
  )
);
const TrafficChart = dynamic(() =>
  import("./TrafficChart").then((mod) => mod.TrafficChart)
);

export function AnalyticsCharts() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">Analytics</h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <TrafficChart />
        <ApiUsageChart />
        <ResourceUtilizationChart />
      </div>
    </div>
  );
}
