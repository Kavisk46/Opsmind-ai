import dynamic from "next/dynamic";

import { AIInsights } from "./AIInsights";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { HeroSection } from "./HeroSection";
import { QuickActions } from "./QuickActions";
import { RecentActivity } from "./RecentActivity";
import { ServerStatus } from "./ServerStatus";
import { StatsCards } from "./StatsCards";
import { SystemHealth } from "./SystemHealth";
import { TeamWorkspace } from "./TeamWorkspace";

// Dynamically imported so recharts (and this chart's own bundle weight)
// loads in its own chunk instead of the Dashboard's main bundle.
const AIStatus = dynamic(() =>
  import("./AIStatus").then((mod) => mod.AIStatus)
);

export function Dashboard() {
  return (
    <div className="space-y-6">
      <HeroSection />
      <StatsCards />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <AIStatus />
        <TeamWorkspace />
      </div>
      <AnalyticsCharts />
      <AIInsights />
      <SystemHealth />
      <ServerStatus />
      <QuickActions />
      <RecentActivity />
    </div>
  );
}
