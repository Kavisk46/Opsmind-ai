import { ApiUsageChart } from "./ApiUsageChart";
import { ResourceUtilizationChart } from "./ResourceUtilizationChart";
import { TrafficChart } from "./TrafficChart";

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
