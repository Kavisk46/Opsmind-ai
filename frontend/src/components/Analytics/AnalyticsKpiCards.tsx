"use client";

import { Activity, CheckCircle2, Clock, Users } from "lucide-react";

import { StatCard } from "@/components/Cards/StatCard";
import { ApiError } from "@/lib/api";
import activeUsersData from "@/lib/mock-data/analytics-active-users.json";

import { useAiMetricsSummary } from "./analytics-api";
import {
  average,
  percentChange,
  previousPeriodSlice,
  sliceByRange,
} from "./analytics-utils";
import type { ActiveUsersPoint, TimeRange } from "./types";

const activeUsers = activeUsersData as ActiveUsersPoint[];

interface AnalyticsKpiCardsProps {
  timeRange: TimeRange;
}

function roundedChange(current: number, previous: number): number {
  return Math.round(percentChange(current, previous) * 10) / 10;
}

// "Avg. Active Users" has no backend equivalent at all — this app has no
// session/user-activity tracking anywhere (verified: no such concept
// exists in AIMetricsService.summary() or anywhere else in the backend).
// Left on the same mock data/timeRange behavior as before; the other
// three cards below are real. See analytics-api.ts for why they're a
// flat admin-only snapshot rather than a time-series like this one.
export function AnalyticsKpiCards({ timeRange }: AnalyticsKpiCardsProps) {
  // useAiMetricsSummary() is a plain useQuery() — cached (60s staleTime,
  // see lib/query-client.ts) and SHARED with StatsCards.tsx via the same
  // query key, so whichever of the two mounts second gets an instant
  // cache hit instead of a second request to this admin-gated endpoint.
  const { data: summary, isPending, error } = useAiMetricsSummary();
  const isForbidden = error instanceof ApiError && error.status === 403;

  const currentUsers = sliceByRange(activeUsers, timeRange);
  const avgUsers = average(currentUsers.map((point) => point.users));
  const previousAvgUsers = average(
    previousPeriodSlice(activeUsers, timeRange).map((point) => point.users)
  );
  const usersChange = roundedChange(avgUsers, previousAvgUsers);

  const successRatePercent =
    summary && summary.totalRequests > 0
      ? (summary.successCount / summary.totalRequests) * 100
      : null;

  const cardsForState = (): {
    queriesValue: string;
    responseValue: string;
    successValue: string;
  } => {
    if (isForbidden) {
      return {
        queriesValue: "Admin access required",
        responseValue: "Admin access required",
        successValue: "Admin access required",
      };
    }
    if (error) {
      return {
        queriesValue: "Unavailable",
        responseValue: "Unavailable",
        successValue: "Unavailable",
      };
    }
    if (isPending) {
      return { queriesValue: "…", responseValue: "…", successValue: "…" };
    }
    return {
      queriesValue: summary.totalRequests.toLocaleString(),
      responseValue:
        summary.avgLatencyMs !== null
          ? `${Math.round(summary.avgLatencyMs)}ms`
          : "No data yet",
      successValue:
        successRatePercent !== null ? `${successRatePercent.toFixed(1)}%` : "No data yet",
    };
  };

  const { queriesValue, responseValue, successValue } = cardsForState();

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* These three are a live, history-free snapshot (at most the last
          200 recorded requests — see analytics-api.ts) — there's no
          previous-period figure to compare against, so `change` is always
          null here rather than a fabricated percentage. */}
      <StatCard
        label="Total AI Queries"
        value={queriesValue}
        change={null}
        icon={Activity}
      />
      <StatCard
        label="Avg. Response Time"
        value={responseValue}
        change={null}
        icon={Clock}
      />
      <StatCard
        label="API Success Rate"
        value={successValue}
        change={null}
        icon={CheckCircle2}
      />
      <StatCard
        label="Avg. Active Users"
        value={Math.round(avgUsers).toLocaleString()}
        change={usersChange}
        isPositive={usersChange >= 0}
        icon={Users}
      />
    </div>
  );
}
