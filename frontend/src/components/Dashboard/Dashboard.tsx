import { AIInsights } from "./AIInsights";
import { AIStatus } from "./AIStatus";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { HeroSection } from "./HeroSection";
import { QuickActions } from "./QuickActions";
import { RecentActivity } from "./RecentActivity";
import { ServerStatus } from "./ServerStatus";
import { StatsCards } from "./StatsCards";
import { SystemHealth } from "./SystemHealth";
import { TeamWorkspace } from "./TeamWorkspace";

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
