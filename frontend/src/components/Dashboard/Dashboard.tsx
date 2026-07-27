"use client";

import { useSimulatedLoad } from "@/hooks/use-simulated-load";

import { AIInsights } from "./AIInsights";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardSkeleton } from "./DashboardSkeleton";
import { HealthCards } from "./HealthCards";
import { QuickAccess } from "./QuickAccess";
import { RecentConversations } from "./RecentConversations";
import { RecentDocuments } from "./RecentDocuments";
import { StatsGrid } from "./StatsGrid";
import { Timeline } from "./Timeline";

export function Dashboard() {
  const isLoading = useSimulatedLoad();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-8">
      <DashboardHeader />
      <StatsGrid />
      <AIInsights />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <RecentDocuments className="xl:col-span-2" />
        <RecentConversations />
      </div>
      <Timeline />
      <AnalyticsCharts />
      <HealthCards />
      <QuickAccess />
    </div>
  );
}
